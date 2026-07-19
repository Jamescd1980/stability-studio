"""Image generation for voice: Pi queues ComfyUI; Myra locks cast; Nari expands scene.

Flow:
  1) STT name fixes
  2) Myra cast_resolve (character/show lists) — ask if unclear
  3) Nari expands scene with locked trigger (chat only, no MCP)
  4) Queue ComfyUI with LoRA nodes when cast resolved
  5) Deliver still to Windows ComfyBox Images via Orla ingest
"""
from __future__ import annotations

import copy
import logging
import re
import time
import uuid

import requests

from . import cast_resolve

log = logging.getLogger("studio_edge.generate")

_BASE_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 0,
            "steps": 28,
            "cfg": 6.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
    },
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "studio_edge", "images": ["8", 0]}},
}

_STT_NAME_FIXES = (
    (re.compile(r"\bfirm\b", re.I), "Fern"),
    (re.compile(r"\bhejin\s+park\b", re.I), "Park Heejin"),
    (re.compile(r"\bpark\s+hejin\b", re.I), "Park Heejin"),
    (re.compile(r"\bheejin\s+park\b", re.I), "Park Heejin"),
)


def correct_stt_names(description: str) -> str:
    text = description or ""
    for pat, repl in _STT_NAME_FIXES:
        text = pat.sub(repl, text)
    return text


def expand_prompt_via_jan(brain, description: str) -> str:
    """Fast prompt expand via Nari chat (no MCP)."""
    if brain is None:
        return description
    old_mode = getattr(brain, "api_mode", "server")
    old_timeout = getattr(brain, "timeout_s", 180)
    try:
        brain.api_mode = "chat"
        brain.timeout_s = min(int(old_timeout), 45)
        directive = (
            "Write ONE Illustrious/anime positive prompt for this scene. "
            "If a Character= and trigger= are given, you MUST keep that exact trigger token "
            "and character identity. Danbooru-style tags, under 80 tokens, no markdown, "
            "no negatives, no explanation. "
            f"Scene: {description}"
        )
        reply = brain.instruct(directive, allow_chat_fallback=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("Prompt expand failed: %s", exc)
        reply = ""
    finally:
        brain.api_mode = old_mode
        brain.timeout_s = old_timeout

    prompt = (reply or "").strip().strip('"').strip()
    if not prompt or len(prompt) < 8:
        return description
    return prompt.split("\n")[0][:500]


def _attach_loras(wf: dict, loras: list[dict]) -> dict:
    """Chain LoraLoader nodes after checkpoint; rewire model/clip consumers."""
    if not loras:
        return wf
    model_ref: list = ["4", 0]
    clip_ref: list = ["4", 1]
    node_id = 20
    for item in loras:
        name = str(item.get("file") or "").strip()
        if not name:
            continue
        w = float(item.get("weight", 0.8))
        nid = str(node_id)
        wf[nid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": name,
                "strength_model": w,
                "strength_clip": w,
                "model": model_ref,
                "clip": clip_ref,
            },
        }
        model_ref = [nid, 0]
        clip_ref = [nid, 1]
        node_id += 1
    wf["3"]["inputs"]["model"] = model_ref
    wf["6"]["inputs"]["clip"] = clip_ref
    wf["7"]["inputs"]["clip"] = clip_ref
    return wf


def _ensure_trigger(prompt: str, trigger: str | None) -> str:
    if not trigger:
        return prompt
    if trigger.lower() in prompt.lower():
        return prompt
    return f"{trigger}, {prompt}"


def _deliver_to_orla(
    cfg: dict,
    *,
    comfy_url: str,
    images: list[dict],
    asked: str,
    expanded_prompt: str,
    prompt_id: str,
    cast: dict | None = None,
) -> list[str]:
    orla_cfg = cfg.get("orla") or {}
    gen = cfg.get("generation") or {}
    if not gen.get("deliver_to_orla", True):
        return []
    tools_url = str(orla_cfg.get("tools_url") or "http://192.168.50.42:11436").rstrip("/")
    delivered: list[str] = []
    batch_names = [str(img.get("filename") or "") for img in images if img.get("filename")]
    for img in images:
        filename = str(img.get("filename") or "")
        if not filename:
            continue
        payload = {
            "action": "ingest",
            "comfyui_url": comfy_url,
            "filename": filename,
            "subfolder": img.get("subfolder") or "",
            "type": img.get("type") or "output",
            "asked": asked,
            "expanded_prompt": expanded_prompt,
            "prompt_id": prompt_id,
            "batch": batch_names,
            "source": "myra_voice",
            "cast": (cast or {}).get("id") if cast else None,
        }
        try:
            r = requests.post(f"{tools_url}/action", json=payload, timeout=90)
            data = r.json() if r.content else {}
        except requests.RequestException as exc:
            log.warning("Orla ingest failed for %s: %s", filename, exc)
            continue
        if data.get("ok") and data.get("path"):
            delivered.append(str(data["path"]))
            log.info("Delivered %s → %s", filename, data["path"])
        else:
            log.warning("Orla ingest error for %s: %s", filename, data.get("error"))
    return delivered


def generate_via_comfyui(
    description: str,
    cfg: dict,
    *,
    positive_prompt: str | None = None,
    loras: list[dict] | None = None,
    cast: dict | None = None,
) -> str:
    gen = cfg.get("generation", {})
    url = gen.get("comfyui_url", "http://192.168.50.57:8188").rstrip("/")
    prompt = (positive_prompt or description or "").strip() or description
    if cast and cast.get("trigger"):
        prompt = _ensure_trigger(prompt, str(cast["trigger"]))
    negative = gen.get(
        "default_negative",
        "lowres, bad anatomy, worst quality, watermark, signature, text",
    )

    wf = copy.deepcopy(_BASE_WORKFLOW)
    # Prefer waijfu / v170 when cast asks for it via preferred_style mapping in config
    ckpt = gen.get("default_checkpoint", "waiIllustriousSDXL_v160.safetensors")
    if cast and cast.get("preferred_style") == "waijfu":
        ckpt = gen.get("waijfu_checkpoint", ckpt)
    wf["4"]["inputs"]["ckpt_name"] = ckpt
    wf["5"]["inputs"]["width"] = int(gen.get("width", 832))
    wf["5"]["inputs"]["height"] = int(gen.get("height", 1216))
    wf["3"]["inputs"]["steps"] = int(gen.get("steps", 28))
    wf["3"]["inputs"]["cfg"] = float(gen.get("cfg", 6.0))
    wf["3"]["inputs"]["sampler_name"] = gen.get("sampler", "euler_ancestral")
    wf["3"]["inputs"]["scheduler"] = gen.get("scheduler", "normal")
    wf["3"]["inputs"]["seed"] = uuid.uuid4().int % (2**32)
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["text"] = negative
    _attach_loras(wf, loras or [])

    try:
        health = requests.get(f"{url}/system_stats", timeout=5)
        health.raise_for_status()
    except requests.RequestException as exc:
        log.error("ComfyUI not reachable at %s: %s", url, exc)
        return "I can't reach ComfyUI on the studio box right now."

    try:
        client_id = str(uuid.uuid4())
        r = requests.post(
            f"{url}/prompt",
            json={"prompt": wf, "client_id": client_id},
            timeout=30,
        )
        r.raise_for_status()
        prompt_id = r.json().get("prompt_id")
    except requests.RequestException as exc:
        log.error("ComfyUI queue failed: %s", exc)
        return "ComfyUI rejected the job. Check the checkpoint or LoRA names."

    if not prompt_id:
        return "ComfyUI didn't accept the job."

    log.info(
        "Queued ComfyUI %s cast=%s loras=%s prompt=%r",
        prompt_id,
        (cast or {}).get("id"),
        [x.get("file") for x in (loras or [])],
        prompt[:120],
    )
    deadline = time.time() + int(gen.get("timeout_s", 300))
    try:
        while time.time() < deadline:
            h = requests.get(f"{url}/history/{prompt_id}", timeout=15).json()
            if prompt_id in h:
                status = h[prompt_id].get("status") or {}
                if status.get("completed") or h[prompt_id].get("outputs"):
                    outs = h[prompt_id].get("outputs") or {}
                    images: list[dict] = []
                    for node in outs.values():
                        for img in node.get("images") or []:
                            if img.get("filename"):
                                images.append(img)
                    if not images:
                        return "Done. Your image is ready on the studio box."
                    names = [str(i["filename"]) for i in images]
                    delivered = _deliver_to_orla(
                        cfg,
                        comfy_url=url,
                        images=images,
                        asked=description,
                        expanded_prompt=prompt,
                        prompt_id=str(prompt_id),
                        cast=cast,
                    )
                    who = (cast or {}).get("display_name") or "scene"
                    if delivered:
                        return f"Done. Saved {names[0]} ({who}) to ComfyBox Images on the main PC."
                    return (
                        f"Done. Saved {names[0]} on ComfyBox; "
                        "Windows delivery failed — check Orla tools."
                    )
                if status.get("status_str") == "error":
                    return "ComfyUI hit an error while rendering."
            time.sleep(2)
        return "It's still rendering on the studio box; I'll leave it running."
    except requests.RequestException as exc:
        log.error("ComfyUI poll failed: %s", exc)
        return "I queued the image, but lost contact while waiting."


def generate(brain, description: str, cfg: dict) -> str:
    """Voice image path: cast resolve → Nari expand → ComfyUI (+ LoRAs)."""
    gen = cfg.get("generation") or {}
    route = (gen.get("route") or "comfyui").lower()
    if route == "jan_mcp":
        return (
            "The Jan MCP generate path is disabled. "
            "Set generation.route to comfyui for voice images."
        )

    asked = correct_stt_names((description or "").strip())
    if asked != (description or "").strip():
        log.info("STT name correction: %r → %r", description, asked)

    resolved = cast_resolve.resolve_cast(asked)
    if resolved.get("need_clarify"):
        return str(resolved.get("ask") or "Which character did you want?")
    if resolved.get("ok") is False and resolved.get("error"):
        return str(resolved["error"])

    cast = resolved.get("character")
    loras = cast_resolve.loras_for_comfy(resolved)
    nari_input = cast_resolve.directive_for_nari(asked, resolved)

    prompt = nari_input
    if brain is not None and gen.get("expand_prompt", True):
        prompt = expand_prompt_via_jan(brain, nari_input)
        log.info("Expanded prompt: %s", prompt[:200])

    return generate_via_comfyui(
        asked, cfg, positive_prompt=prompt, loras=loras, cast=cast
    )

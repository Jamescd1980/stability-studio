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
from pathlib import Path

import requests

from . import cast_resolve
from .prompt_sex_lexicon import (
    CAMERA_PROP_NEGATIVE,
    SEX_PROMPT_DIRECTIVE,
    SOFT_TO_EXPLICIT,
)

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
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]}},
}

_STT_NAME_FIXES = (
    (re.compile(r"\bfirm\b", re.I), "Fern"),
    (re.compile(r"\bfern\b", re.I), "Fern"),
    # Frieren — Hailo: frayer in / ferry / free rin
    (re.compile(r"\ba\s+frayer\s+in\b", re.I), "Frieren"),
    (re.compile(r"\bfrayer\s+in\b", re.I), "Frieren"),
    (re.compile(r"\bfrayerin\b", re.I), "Frieren"),
    (re.compile(r"\bfreiren\b", re.I), "Frieren"),
    (re.compile(r"\bfree\s+rin\b", re.I), "Frieren"),
    (re.compile(r"\bferry\s+in\b", re.I), "Frieren"),
    (re.compile(r"\bferrien\b", re.I), "Frieren"),
    (re.compile(r"\bfrieren\b", re.I), "Frieren"),
    # Character-slot only mangling: bare "Ferry" / "Frayer" (not ferry boat contexts)
    (re.compile(
        r"\b(?:character\s+(?:is\s+|to\s+|named\s+)?)?(?:a\s+)?(?:ferry|frayer)\b",
        re.I,
    ), "Frieren"),
    # Flamme — flame / flam
    (re.compile(r"\bflamme\b", re.I), "Flamme"),
    (re.compile(r"\bflame\b", re.I), "Flamme"),
    (re.compile(r"\bflam\b", re.I), "Flamme"),
    (re.compile(r"\bflama\b", re.I), "Flamme"),
    # Gold standard (voice)
    (re.compile(r"\bgold\s+standard\b", re.I), "gold standard"),
    (re.compile(r"\bgold\s+standered\b", re.I), "gold standard"),
    (re.compile(r"\bgolds\s+standard\b", re.I), "gold standard"),
    (re.compile(r"\bhijing(?:\s+park)?\b", re.I), "Park Heejin"),
    (re.compile(r"\bhijin(?:\s+park)?\b", re.I), "Park Heejin"),
    (re.compile(r"\bhe[\s\-]?jin(?:\s+park)?\b", re.I), "Park Heejin"),
    (re.compile(r"\bhe\s+jean(?:\s+park(?:ed)?)?\b", re.I), "Park Heejin"),
    (re.compile(r"\bhejin(?:\s+park)?\b", re.I), "Park Heejin"),
    (re.compile(r"\bpark\s+he[\s\-]?jin\b", re.I), "Park Heejin"),
    (re.compile(r"\bheejin(?:\s+park)?\b", re.I), "Park Heejin"),
    (re.compile(r"\bpark\s+heejin\b", re.I), "Park Heejin"),
    (re.compile(r"\bso\s+low\s+leveling\b", re.I), "Solo Leveling"),
    (re.compile(r"\bsolo\s+leveling\b", re.I), "Solo Leveling"),
    (re.compile(r"\bwafer\s+alfa\b", re.I), "waijfu"),
    (re.compile(r"\bwaffer\s+alpha\b", re.I), "waijfu"),
    (re.compile(r"\bwageful\b", re.I), "waijfu"),
    (re.compile(r"\bwage\s*full\b", re.I), "waijfu"),
    (re.compile(r"\bubele\b", re.I), "Ubel"),
    (re.compile(r"\boebel\b", re.I), "Ubel"),
    (re.compile(r"\boo[\s\-]?bell\b", re.I), "Ubel"),
    (re.compile(r"\bubell\b", re.I), "Ubel"),
    # Hailo often mangles Übel → "will you" / "o bell" / "you bell"
    (re.compile(r"\bwill\s+you\s+(?:see\s+)?(?:actual\s+)?(?:the\s+)?character\b", re.I), "Ubel"),
    (re.compile(r"\byou\s+bell\b", re.I), "Ubel"),
    (re.compile(r"\bo+\s*bell\b", re.I), "Ubel"),
    (re.compile(r"\bnauri\b", re.I), "Nari"),
    (re.compile(r"\bnaree\b", re.I), "Nari"),
    # recreate / studio agent id spoken forms (canonical gallery prefix)
    (re.compile(r"\bre[\s\-]?create\b", re.I), "recreate"),
    (re.compile(r"\bstudio\s+edge\b", re.I), "studio agent"),
)


def correct_stt_names(description: str) -> str:
    text = description or ""
    # Idempotent: collapse already-correct forms first
    text = re.sub(r"\bpark\s+park\s+heejin\b", "Park Heejin", text, flags=re.I)
    text = re.sub(r"\bpark\s+heejin\b", "Park Heejin", text, flags=re.I)
    for pat, repl in _STT_NAME_FIXES:
        # Avoid Park Heejin → Park Park Heejin when a later rule matches Heejin
        if repl == "Park Heejin" and re.search(r"\bpark\s+heejin\b", text, re.I):
            continue
        text = pat.sub(repl, text)
    text = re.sub(r"\bpark\s+park\s+heejin\b", "Park Heejin", text, flags=re.I)
    return text


def _scene_nonempty(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 8:
        return False
    # Pose/scene locked to source image counts as a real scene answer
    if re.search(
        r"(?i)\bsame\s+as\s+source\b|\boriginal\s+(?:image|picture)\b|"
        r"\bsame\s+(?:exact\s+)?(?:scene|layout|pose)\b",
        t,
    ):
        return True
    # Reject crumbs that are only cast boilerplate
    if re.fullmatch(r"(?i)(?:character|trigger|style)\s*=.*", t):
        return False
    return True


_DIRECTIVE_LEAK_RE = re.compile(
    r"(?i)\b(?:keep trigger token|do not invent|do not ask questions|"
    r"scene request:|lock pose from the stage|lock scene/setting|"
    r"prior prompt to respect|character=|trigger=)",
)


def looks_like_comfy_prompt(text: str) -> bool:
    """True if text is usable Illustrious/Danbooru tags, not a Nari instruction memo."""
    t = (text or "").strip()
    if len(t) < 12:
        return False
    if _DIRECTIVE_LEAK_RE.search(t) and t.count(",") < 3:
        return False
    # Instruction memos are long prose with few commas
    if "Do not invent" in t or "Scene request:" in t:
        return False
    return True


def build_fallback_prompt(
    asked: str,
    cast: dict | None,
    *,
    scene_hint: str = "",
    locks: list[str] | None = None,
) -> str:
    """Deterministic tag prompt when Nari expand is off/failed — never send directives to Comfy."""
    locks = locks or []
    bits: list[str] = []
    if cast:
        trig = str(cast.get("trigger") or "").strip()
        if trig:
            bits.append(trig)
        helpers = str(cast.get("caption_helpers") or "").strip()
        if helpers:
            bits.append(helpers)
        name = str(cast.get("display_name") or cast.get("id") or "").strip()
        if name:
            bits.append(name)
        if cast.get("gender") == "female":
            bits.append("1girl, solo")
        elif cast.get("gender") == "male":
            bits.append("1boy, solo")
    raw = correct_stt_names((scene_hint or asked or "").strip())
    # Drop English lock/instruction crumbs; keep visual nouns
    raw = _DIRECTIVE_LEAK_RE.sub(" ", raw)
    raw = re.sub(
        r"(?i)\b(?:keep|exact|same|character|trigger|gold standard|adjustment|"
        r"recreate source|source file|enhance detail only|where possible|"
        r"do not|must|please|say yes)\b",
        " ",
        raw,
    )
    raw = re.sub(r"\s+", " ", raw).strip(" .,;:")
    if raw:
        bits.append(raw)
    # Soft pose/scene wording only as tags, not LOCK memos
    if "pose" in locks:
        bits.append("same pose")
    if "scene" in locks:
        bits.append("same background")
    # Default NSFW cleanliness unless user asked for fluids
    low = f"{asked} {scene_hint}".lower()
    if not re.search(r"\b(?:cum|semen|aftersex|creampie)\b", low):
        pass  # negatives handle this
    prompt = ", ".join(b for b in bits if b)
    return prompt[:500] if prompt else (asked or "1girl")[:500]


def expand_prompt_via_jan(
    brain,
    description: str,
    *,
    locks: list[str] | None = None,
    require_scene: bool = False,
) -> str:
    """Fast prompt expand via Nari chat (no MCP)."""
    if require_scene and not _scene_nonempty(description):
        return ""
    if brain is None:
        return description
    locks = locks or []
    old_mode = getattr(brain, "api_mode", "server")
    old_timeout = getattr(brain, "timeout_s", 180)
    try:
        brain.api_mode = "chat"
        brain.timeout_s = min(int(old_timeout), 45)
        lock_bits = []
        if "pose" in locks:
            lock_bits.append("Do not change pose.")
        if "scene" in locks:
            lock_bits.append("Do not change scene or background.")
        directive = (
            "Write ONE Illustrious/anime positive prompt for this scene. "
            "If a Character= and trigger= are given, you MUST keep that exact trigger token "
            "and character identity. Danbooru-style tags, under 80 tokens, no markdown, "
            "no negatives, no explanation, no question marks. "
            "Do not invent a different character or a random setting if Scene is given. "
            f"{SEX_PROMPT_DIRECTIVE} "
            + (" ".join(lock_bits) + " " if lock_bits else "")
            + f"Scene: {description}"
        )
        reply = brain.instruct(directive, allow_chat_fallback=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("Prompt expand failed: %s", exc)
        reply = ""
    finally:
        brain.api_mode = old_mode
        brain.timeout_s = old_timeout

    prompt = (reply or "").strip().strip('"').strip()
    if prompt.endswith("?"):
        prompt = prompt.rstrip("?").strip()
    if not prompt or len(prompt) < 8:
        return description
    # Reject Nari inventing Character= when we already locked one
    line = prompt.split("\n")[0][:500]
    return _harden_sex_prompt(line)


def _harden_sex_prompt(text: str) -> str:
    """Blunt soft euphemisms; strip camera-prop wording from positives."""
    out = text or ""
    for pat, repl in SOFT_TO_EXPLICIT:
        out = re.sub(pat, repl, out, flags=re.I)
    out = re.sub(r"\bcameras?\b", "view", out, flags=re.I)
    out = re.sub(r"\bdslr\b|\bcamcorder\b", "", out, flags=re.I)
    return re.sub(r",\s*,", ", ", out).strip(" ,")


def _orla_action(cfg: dict, body: dict, *, timeout: float = 30) -> dict:
    orla_cfg = cfg.get("orla") or {}
    tools_url = str(orla_cfg.get("tools_url") or "http://192.168.50.42:11436").rstrip("/")
    try:
        r = requests.post(f"{tools_url}/action", json=body, timeout=timeout)
        return r.json() if r.content else {}
    except requests.RequestException as exc:
        log.warning("Orla action %s failed: %s", body.get("action"), exc)
        return {"ok": False, "error": str(exc)}


def resolve_source_meta(cfg: dict, selector: str = "last_displayed") -> dict:
    """Resolve gallery image + sidecar via Orla."""
    data = _orla_action(
        cfg,
        {"action": "resolve", "selector": selector or "last_displayed", "kind": "image"},
    )
    if not data.get("ok"):
        return data
    path = data.get("path")
    meta = _orla_action(cfg, {"action": "get_meta", "path": path})
    if meta.get("ok"):
        data["meta"] = meta.get("meta") or {}
        data["sidecar"] = meta.get("sidecar")
    else:
        data["meta"] = {}
    return data


def notify_orla_job(
    cfg: dict,
    *,
    event: str,
    path: str = "",
    prompt_id: str = "",
    cast_id: str | None = None,
    batch_id: str = "",
    display_please: bool = False,
) -> None:
    body = {
        "action": "handoff",
        "from": "nari",
        "to": "orla",
        "event": event,
        "path": path,
        "prompt_id": prompt_id,
        "cast_id": cast_id,
        "batch_id": batch_id,
    }
    if display_please or event == "display_please":
        body["event"] = "display_please"
    _orla_action(cfg, body, timeout=15)


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
            notify_orla_job(
                cfg,
                event="done",
                path=str(data["path"]),
                prompt_id=prompt_id,
                cast_id=(cast or {}).get("id") if cast else None,
            )
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
    quality: str | None = None,
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
    # Guard: refuse to send Nari memos into Comfy
    if not looks_like_comfy_prompt(prompt):
        log.error("Refusing directive-leak prompt; rebuilding tags")
        prompt = build_fallback_prompt(description, cast, scene_hint=description)
    prompt = _harden_sex_prompt(prompt)
    hint = f"{description} {positive_prompt or ''}".lower()
    # Solo beach / portrait: suppress crowd + unsolicited fluids
    if not re.search(r"\b(?:cum|semen|creampie|aftersex|bukkake)\b", hint):
        negative = (
            f"{negative}, cum, semen, excessive bodily fluids, aftersex"
        )
    if re.search(r"\b(?:beach|solo|1girl)\b", hint) and not re.search(
        r"\b(?:couple|2boys|multiple boys|threesome|group)\b", hint
    ):
        negative = f"{negative}, 2boys, multiple boys, crowd, extra people"
    if CAMERA_PROP_NEGATIVE.lower() not in negative.lower():
        negative = f"{negative}, {CAMERA_PROP_NEGATIVE}"
    use_loras = list(loras or [])
    prompt, negative, use_loras, q_over = apply_quality(
        prompt=prompt,
        negative=negative,
        loras=use_loras,
        gen=gen,
        quality=quality,
        text_hint=f"{description} {positive_prompt or ''}",
    )

    wf = copy.deepcopy(_BASE_WORKFLOW)
    # 00009 / gold bar is house default; cast preferred_style can still pin waijfu
    ckpt = gen.get("default_checkpoint", "waijfu_alpha.safetensors")
    if q_over.get("quality") == "gold_standard" or gen.get("quality_default") == "gold_standard":
        ckpt = gen.get("gold_checkpoint") or ckpt
    if cast and cast.get("preferred_style") == "waijfu":
        ckpt = gen.get("waijfu_checkpoint") or gen.get("gold_checkpoint") or ckpt
    wf["4"]["inputs"]["ckpt_name"] = ckpt
    wf["5"]["inputs"]["width"] = int(gen.get("width", 832))
    wf["5"]["inputs"]["height"] = int(gen.get("height", 1472))
    steps = q_over.get("steps") if q_over.get("steps") is not None else gen.get("steps", 36)
    cfg_v = q_over.get("cfg") if q_over.get("cfg") is not None else gen.get("cfg", 6.5)
    wf["3"]["inputs"]["steps"] = int(steps)
    wf["3"]["inputs"]["cfg"] = float(cfg_v)
    wf["3"]["inputs"]["sampler_name"] = gen.get("sampler", "euler_ancestral")
    wf["3"]["inputs"]["scheduler"] = gen.get("scheduler", "normal")
    wf["3"]["inputs"]["seed"] = uuid.uuid4().int % (2**32)
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["text"] = negative
    _attach_loras(wf, use_loras)

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


# Voice "gold standard" → recreate_003 / illustrious_detail_hero bar
_QUALITY_RE = re.compile(
    r"\b(?:gold\s+standard|detail\s+hero|absurdres\s+quality|hero\s+quality)\b",
    re.I,
)
QUALITY_PROFILES: dict[str, dict] = {
    # Matches studio_agent_00009 finish stack (eyes + lens flare + detailer)
    "gold_standard": {
        "steps": 36,
        "cfg": 6.5,
        "prompt_tail": (
            "highly detailed, intricate, sharp focus, absurdres, highres, "
            "perfect eyes, eye_focus, detailed skin, micro hair detail"
        ),
        "negative_extra": (
            "plastic skin, soft face, muddy shading, flat color, oversmoothed, "
            "anatomical artifact, deformed crotch, blurry face, extra flesh"
        ),
        "loras": [
            {
                "file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
                "weight": 0.75,
            },
            {
                "file": "LensFlare_LightLeak_IL.safetensors",
                "weight": 0.55,
            },
            {"file": "ILDetailerV2.safetensors", "weight": 0.65},
        ],
    },
}


def detect_quality(text: str) -> tuple[str | None, dict]:
    """Return (quality_name, profile) if the utterance demands a finish bar."""
    if _QUALITY_RE.search(text or ""):
        return "gold_standard", dict(QUALITY_PROFILES["gold_standard"])
    return None, {}


def apply_quality(
    *,
    prompt: str,
    negative: str,
    loras: list[dict],
    gen: dict,
    quality: str | None = None,
    text_hint: str = "",
) -> tuple[str, str, list[dict], dict]:
    """Merge gold-standard (or named) profile into prompt/neg/loras/sampler overrides."""
    name = quality
    profile: dict = {}
    if not name:
        name, profile = detect_quality(text_hint or prompt)
    elif name in QUALITY_PROFILES:
        profile = dict(QUALITY_PROFILES[name])
    if not profile and gen.get("quality_default") in QUALITY_PROFILES:
        name = str(gen.get("quality_default"))
        profile = dict(QUALITY_PROFILES[name])
    if not profile:
        return prompt, negative, loras, {}

    tail = str(profile.get("prompt_tail") or "").strip()
    if tail and tail.lower() not in (prompt or "").lower():
        prompt = f"{prompt.rstrip(', ')}, {tail}"
    neg_x = str(profile.get("negative_extra") or "").strip()
    if neg_x:
        negative = f"{negative}, {neg_x}" if negative else neg_x
    # Dedupe LoRAs by filename; cast LoRAs keep priority, then quality stack
    seen = {str(x.get("file") or "").lower() for x in loras if x.get("file")}
    merged = list(loras)
    for item in profile.get("loras") or []:
        fn = str(item.get("file") or "")
        if not fn or fn.lower() in seen:
            continue
        merged.append(dict(item))
        seen.add(fn.lower())
    overrides = {
        "steps": profile.get("steps"),
        "cfg": profile.get("cfg"),
        "quality": name,
    }
    log.info("Quality profile=%s steps=%s cfg=%s", name, overrides.get("steps"), overrides.get("cfg"))
    return prompt, negative, merged, overrides


def abort_jobs(cfg: dict) -> None:
    """Hard-stop Comfy queue/current job and best-effort kill local playback."""
    import subprocess

    gen = cfg.get("generation") or {}
    url = str(gen.get("comfyui_url") or "http://192.168.50.57:8188").rstrip("/")
    try:
        requests.post(f"{url}/interrupt", timeout=3)
        log.info("ComfyUI interrupt sent")
    except requests.RequestException as exc:
        log.debug("Comfy interrupt failed: %s", exc)
    try:
        requests.post(
            f"{url}/queue",
            json={"clear": True},
            timeout=3,
        )
        log.info("ComfyUI queue cleared")
    except requests.RequestException as exc:
        log.debug("Comfy queue clear failed: %s", exc)
    # Stop Pi speakers mid-sentence if something is playing
    for cmd in (
        ["pkill", "-f", "aplay"],
        ["pkill", "-f", "paplay"],
        ["pkill", "-f", "ffplay"],
    ):
        try:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def generate(
    brain,
    description: str,
    cfg: dict,
    *,
    require_scene: bool = False,
    scene_hint: str = "",
    locks: list[str] | None = None,
    base_prompt: str = "",
    require_cast: bool = False,
    quality: str | None = None,
) -> str:
    """Voice image path: cast resolve → Nari expand → ComfyUI (+ LoRAs)."""
    gen = cfg.get("generation") or {}
    route = (gen.get("route") or "comfyui").lower()
    if route == "jan_mcp":
        return (
            "The Jan MCP generate path is disabled. "
            "Set generation.route to comfyui for voice images."
        )

    try:
        from . import agent_pulse

        agent_pulse.set_status("nari", "thinking", detail="Cast + prompt")
        agent_pulse.set_status("myra", "working", detail="Hand off to Nari")
    except Exception:
        pass

    asked = correct_stt_names((description or "").strip())
    if asked != (description or "").strip():
        log.info("STT name correction: %r → %r", description, asked)

    scene_check = scene_hint or asked
    if require_scene and not _scene_nonempty(scene_check):
        try:
            from . import agent_pulse

            agent_pulse.set_status("nari", "ready", detail="")
            agent_pulse.set_status("myra", "talking", detail="Need scene")
        except Exception:
            pass
        return "I need a scene or layout before I send this to Nari. What should be happening?"

    resolved = cast_resolve.resolve_cast(asked)
    if resolved.get("need_clarify"):
        try:
            from . import agent_pulse

            agent_pulse.set_status("nari", "ready", detail="")
            agent_pulse.set_status("myra", "talking", detail="Clarify cast")
        except Exception:
            pass
        return str(resolved.get("ask") or "Which character did you want?")
    if resolved.get("ok") is False and resolved.get("error"):
        return str(resolved["error"])

    cast = resolved.get("character")
    if require_cast and not cast:
        try:
            from . import agent_pulse

            agent_pulse.set_status("nari", "ready", detail="")
            agent_pulse.set_status("myra", "talking", detail="Need cast")
        except Exception:
            pass
        return (
            "I won't generate without a matched cast LoRA. "
            "Name the character again — Ubel, Fern, Park Heejin, and so on."
        )
    loras = cast_resolve.loras_for_comfy(resolved)
    # Directive is for Nari only — never the Comfy positive by default
    nari_input = cast_resolve.directive_for_nari(asked, resolved, locks=locks)
    if base_prompt and looks_like_comfy_prompt(base_prompt):
        nari_input = (
            f"{nari_input} Prior prompt to respect: {base_prompt[:400]}"
        )

    prompt = ""
    if brain is not None and gen.get("expand_prompt", True):
        try:
            from . import agent_pulse

            agent_pulse.set_status("nari", "thinking", detail="Expand prompt")
        except Exception:
            pass
        expanded = expand_prompt_via_jan(
            brain, nari_input, locks=locks, require_scene=require_scene
        )
        if expanded and looks_like_comfy_prompt(expanded):
            # Strip Nari inventing fake Character=/trigger= prose
            expanded = re.sub(
                r"(?i)\b(?:keep trigger token|do not invent|do not ask questions|"
                r"scene request:|lock pose from[^.]+\.|lock scene/setting[^.]+\.)\s*",
                "",
                expanded,
            )
            if cast and cast.get("trigger"):
                if str(cast["trigger"]).lower() not in expanded.lower():
                    expanded = f"{cast['trigger']}, {expanded}"
            prompt = expanded.strip()
            log.info("Expanded prompt: %s", prompt[:200])
        elif not expanded and require_scene:
            return "I need a clearer scene before expanding. What's the layout?"

    if not prompt or not looks_like_comfy_prompt(prompt):
        # Prefer a real prior Illustrious prompt (recreate) over directive leak
        if base_prompt and looks_like_comfy_prompt(base_prompt):
            prompt = base_prompt
            if cast and cast.get("trigger") and str(cast["trigger"]).lower() not in prompt.lower():
                prompt = f"{cast['trigger']}, {prompt}"
        else:
            prompt = build_fallback_prompt(
                asked, cast, scene_hint=scene_hint, locks=locks
            )
        log.info("Using fallback/tag prompt: %s", prompt[:200])

    try:
        from . import agent_pulse

        who = (cast or {}).get("display_name") or "scene"
        agent_pulse.set_status("nari", "generating", detail=f"ComfyUI · {who}")
    except Exception:
        pass

    q_name = quality
    if not q_name:
        q_name, _ = detect_quality(f"{asked} {scene_hint} {prompt}")
    if not q_name and (cfg.get("generation") or {}).get("quality_default"):
        q_name = str((cfg.get("generation") or {}).get("quality_default"))

    notify_orla_job(cfg, event="queued", cast_id=(cast or {}).get("id") if cast else None)
    result = generate_via_comfyui(
        asked,
        cfg,
        positive_prompt=prompt,
        loras=loras,
        cast=cast,
        quality=q_name,
    )
    try:
        from . import agent_pulse

        agent_pulse.set_status("nari", "ready", detail="")
    except Exception:
        pass
    return result


def _upload_image_via_orla(cfg: dict, source_path: str, comfy_url: str) -> str | None:
    """Ask Orla (Windows) to upload D:\\ gallery file into Comfy input/."""
    data = _orla_action(
        cfg,
        {
            "action": "upload_to_comfy",
            "path": source_path,
            "comfyui_url": comfy_url,
        },
        timeout=120,
    )
    if not data.get("ok"):
        log.error("Orla upload_to_comfy failed: %s", data.get("error"))
        return None
    return str(data.get("comfy_image") or "")


def _src_name(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").split("/")[-1]


def _strip_cast_tokens(prompt: str) -> str:
    """Remove Illustrious cast triggers / nb_* so a new character can take the scene."""
    text = re.sub(r"\bnb_[a-z0-9_]+\b", "", prompt or "", flags=re.I)
    text = re.sub(r",\s*,", ", ", text)
    return re.sub(r"\s{2,}", " ", text).strip(" ,")


def _gold_ckpt(gen: dict, quality_name: str | None = None) -> str:
    ckpt = str(gen.get("default_checkpoint") or "waijfu_alpha.safetensors")
    if quality_name == "gold_standard" or gen.get("quality_default") == "gold_standard":
        ckpt = str(gen.get("gold_checkpoint") or gen.get("waijfu_checkpoint") or ckpt)
    return ckpt


def _poll_comfy_deliver(
    cfg: dict,
    *,
    url: str,
    prompt_id: str,
    asked: str,
    prompt: str,
    cast: dict | None,
    label: str,
) -> str:
    gen = cfg.get("generation") or {}
    deadline = time.time() + int(gen.get("timeout_s", 300))
    try:
        while time.time() < deadline:
            h = requests.get(f"{url}/history/{prompt_id}", timeout=15).json()
            if prompt_id not in h:
                time.sleep(1.2)
                continue
            outs = h[prompt_id].get("outputs") or {}
            images: list[dict] = []
            for node in outs.values():
                for img in node.get("images") or []:
                    if img.get("filename"):
                        images.append(img)
            if not images:
                return f"Done. {label} is on the studio box."
            delivered = _deliver_to_orla(
                cfg,
                comfy_url=url,
                images=images,
                asked=asked,
                expanded_prompt=prompt,
                prompt_id=str(prompt_id),
                cast=cast,
            )
            name = str(images[0]["filename"])
            if delivered:
                return f"Done. {label} → {name}."
            return f"Done. {label} on ComfyBox as {name}."
        return f"The {label} job timed out."
    except requests.RequestException as exc:
        log.error("%s poll failed: %s", label, exc)
        return f"I queued {label}, but lost contact while waiting."


def generate_via_openpose(
    cfg: dict,
    *,
    source_path: str,
    positive_prompt: str,
    loras: list[dict] | None = None,
    cast: dict | None = None,
    quality: str | None = "gold_standard",
    asked: str = "",
) -> str:
    """Txt2img guided by OpenPose ControlNet extracted from a stage-one still."""
    gen = cfg.get("generation") or {}
    url = str(gen.get("comfyui_url") or "http://192.168.50.57:8188").rstrip("/")
    remote = _upload_image_via_orla(cfg, source_path, url)
    if not remote:
        return (
            "I couldn't upload that image to ComfyUI from the gallery. "
            "Check Orla tools are running on the Windows box."
        )

    prompt = (positive_prompt or "").strip()
    if cast and cast.get("trigger"):
        prompt = _ensure_trigger(prompt, str(cast["trigger"]))
    if not looks_like_comfy_prompt(prompt):
        prompt = build_fallback_prompt(asked or prompt, cast, scene_hint=prompt)
    prompt = _harden_sex_prompt(prompt)
    negative = gen.get(
        "default_negative",
        "lowres, bad anatomy, worst quality, watermark, signature, text",
    )
    if CAMERA_PROP_NEGATIVE.lower() not in negative.lower():
        negative = f"{negative}, {CAMERA_PROP_NEGATIVE}"
    use_loras = list(loras or [])
    prompt, negative, use_loras, q_over = apply_quality(
        prompt=prompt,
        negative=negative,
        loras=use_loras,
        gen=gen,
        quality=quality or "gold_standard",
        text_hint=asked or prompt,
    )
    ckpt = _gold_ckpt(gen, str(q_over.get("quality") or quality))
    cn_file = str(gen.get("openpose_controlnet") or "OpenPoseXL2.safetensors")
    cn_strength = float(gen.get("openpose_strength", 0.85))
    cn_strength = max(0.35, min(1.25, cn_strength))
    width = int(gen.get("width", 832))
    height = int(gen.get("height", 1472))

    wf: dict = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": ckpt},
        },
        "10": {"class_type": "LoadImage", "inputs": {"image": remote}},
        "31": {
            "class_type": "OpenposePreprocessor",
            "inputs": {
                "image": ["10", 0],
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
                "resolution": 512,
            },
        },
        "30": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": cn_file},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["4", 1]},
        },
        "32": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "control_net": ["30", 0],
                "image": ["31", 0],
                "strength": cn_strength,
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": uuid.uuid4().int % (2**32),
                "steps": int(q_over.get("steps") or gen.get("steps", 36)),
                "cfg": float(q_over.get("cfg") or gen.get("cfg", 6.5)),
                "sampler_name": gen.get("sampler", "euler_ancestral"),
                "scheduler": gen.get("scheduler", "normal"),
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["32", 0],
                "negative": ["32", 1],
                "latent_image": ["5", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
        },
    }
    _attach_loras(wf, use_loras)

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
        log.error("openpose queue failed: %s", exc)
        return "ComfyUI rejected the OpenPose ControlNet job."
    if not prompt_id:
        return "ComfyUI didn't accept the OpenPose job."

    src = _src_name(source_path)
    log.info(
        "Queued openpose %s strength=%.2f src=%s prompt=%r",
        prompt_id,
        cn_strength,
        src,
        prompt[:120],
    )
    notify_orla_job(cfg, event="queued", cast_id=(cast or {}).get("id") if cast else None)
    return _poll_comfy_deliver(
        cfg,
        url=url,
        prompt_id=str(prompt_id),
        asked=asked or f"openpose {src}",
        prompt=prompt,
        cast=cast,
        label=f"OpenPose cast from {src} (strength {cn_strength:.2f})",
    )


def approximate_via_img2img(
    cfg: dict,
    *,
    source_path: str,
    adjust_text: str = "",
    quality: str | None = "gold_standard",
    denoise: float | None = None,
    loras: list[dict] | None = None,
    cast: dict | None = None,
) -> str:
    """Any image → Orla uploads → Comfy img2img (no sidecar required)."""
    gen = cfg.get("generation") or {}
    url = str(gen.get("comfyui_url") or "http://192.168.50.57:8188").rstrip("/")
    remote = _upload_image_via_orla(cfg, source_path, url)
    if not remote:
        return (
            "I couldn't upload that image to ComfyUI from the gallery. "
            "Check Orla tools are running on the Windows box."
        )

    adjust = correct_stt_names(adjust_text or "")
    if looks_like_comfy_prompt(adjust):
        prompt = adjust
    else:
        prompt = (
            "masterpiece, best quality, amazing quality, anime illustration, "
            "highly detailed, sharp focus, absurdres"
        )
        if adjust:
            prompt = f"{prompt}, {adjust}"
    if cast and cast.get("trigger"):
        prompt = _ensure_trigger(prompt, str(cast["trigger"]))
    prompt = _harden_sex_prompt(prompt)
    negative = gen.get(
        "default_negative",
        "lowres, bad anatomy, worst quality, watermark, signature, text",
    )
    if CAMERA_PROP_NEGATIVE.lower() not in negative.lower():
        negative = f"{negative}, {CAMERA_PROP_NEGATIVE}"
    use_loras = list(loras or [])
    prompt, negative, use_loras, q_over = apply_quality(
        prompt=prompt,
        negative=negative,
        loras=use_loras,
        gen=gen,
        quality=quality,
        text_hint=f"gold standard {adjust}",
    )
    strength = float(
        denoise
        if denoise is not None
        else gen.get("img2img_denoise", 0.48)
    )
    strength = max(0.25, min(0.78, strength))
    ckpt = _gold_ckpt(gen, quality or "gold_standard")

    wf: dict = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": ckpt},
        },
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": remote},
        },
        "11": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["10", 0], "vae": ["4", 2]},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["4", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": uuid.uuid4().int % (2**32),
                "steps": int(q_over.get("steps") or gen.get("steps", 36)),
                "cfg": float(q_over.get("cfg") or gen.get("cfg", 6.5)),
                "sampler_name": gen.get("sampler", "euler_ancestral"),
                "scheduler": gen.get("scheduler", "normal"),
                "denoise": strength,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["11", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
        },
    }
    _attach_loras(wf, use_loras)

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
        log.error("img2img queue failed: %s", exc)
        return "ComfyUI rejected the image-to-image job."
    if not prompt_id:
        return "ComfyUI didn't accept the image-to-image job."

    src_name = _src_name(source_path)
    log.info(
        "Queued img2img %s denoise=%.2f src=%s prompt=%r",
        prompt_id,
        strength,
        src_name,
        prompt[:120],
    )
    return _poll_comfy_deliver(
        cfg,
        url=url,
        prompt_id=str(prompt_id),
        asked=f"approximate {src_name}. {adjust}".strip(),
        prompt=prompt,
        cast=cast,
        label=f"Approximated {src_name} (img2img denoise {strength:.2f})",
    )


_IDENTITY_STRIP_RE = re.compile(
    r"\b(?:blonde hair|yellow eyes|brown hair|black hair|pink hair|"
    r"red hair|orange hair|blue hair|purple hair|green hair|"
    r"brown eyes|red eyes|pink eyes|heterochromia)\b",
    re.I,
)


def _cast_identity_tags(cast: dict) -> str:
    """Hard identity block so OpenPose swaps don't keep the source face/hair."""
    helpers = str(cast.get("caption_helpers") or "").strip()
    name = str(cast.get("display_name") or cast.get("id") or "").strip()
    trigger = str(cast.get("trigger") or "").strip()
    # Built-ins for common casts when caption_helpers empty
    builtins = {
        "frieren": (
            "elf, pointy ears, long white hair, twintails, green eyes, "
            "pale skin, small breasts, serene expression"
        ),
        "fern": "long purple hair, purple eyes, bangs, pale skin",
        "ubel": "short green hair, green eyes, smirk",
        "park_heejin": "long blonde hair, yellow eyes, sun hat",
        "nb_park_heejin": "long blonde hair, yellow eyes, sun hat",
    }
    cid = str(cast.get("id") or "").lower()
    block = helpers or builtins.get(cid, "")
    parts = [p for p in (trigger, name, block) if p]
    return ", ".join(parts)


def _build_cast_swap_prompt(
    *,
    prior: str,
    cast: dict,
    adjust: str = "",
) -> str:
    scene = _strip_cast_tokens(prior)
    scene = _IDENTITY_STRIP_RE.sub("", scene)
    scene = re.sub(r",\s*,", ", ", scene).strip(" ,")
    if not looks_like_comfy_prompt(scene):
        scene = (
            "masterpiece, best quality, amazing quality, anime illustration, "
            "1girl, solo, same pose, same scene composition"
        )
        if adjust:
            scene = f"{scene}, {adjust}"
    identity = _cast_identity_tags(cast)
    # Identity first — OpenPose locks pose; tags must force the new cast
    prompt = (
        f"masterpiece, best quality, amazing quality, anime illustration, "
        f"{identity}, {scene}"
    )
    prompt = re.sub(r",\s*,", ", ", prompt).strip(" ,")
    if adjust and adjust.lower() not in prompt.lower():
        prompt = f"{prompt}, {adjust}"
    return prompt


def recreate_or_adjust(
    brain,
    cfg: dict,
    *,
    selector: str = "last_displayed",
    adjust_text: str = "",
    locks: list[str] | None = None,
) -> str:
    """Recreate from image: OpenPose/i2i for locks; else prompt remix at 00009 bar.

    Sidecars are optional cache only — any gallery/user image can be used.
    """
    src = resolve_source_meta(cfg, selector)
    if not src.get("ok"):
        return str(src.get("error") or "I couldn't find that source image.")
    meta = src.get("meta") or {}
    path_hint = str(src.get("path") or "")
    asked = correct_stt_names(str(meta.get("asked") or meta.get("you_asked") or ""))
    prior = str(meta.get("expanded_prompt") or meta.get("nari_expanded") or "")
    cast_id = meta.get("cast")
    adjust = correct_stt_names((adjust_text or "").strip())
    gen = cfg.get("generation") or {}
    mode = str(gen.get("cast_swap_mode") or "openpose").lower()

    # Prefer real Illustrious tags from PNG workflow / usable sidecar
    if not looks_like_comfy_prompt(prior):
        prior = ""
    if not cast_id and path_hint:
        hit = cast_resolve.match_character(path_hint.replace("\\", " ").replace("/", " "))
        if hit:
            cast_id = hit.get("id") or hit.get("display_name")
    if not cast_id and prior:
        m = re.search(r"\b(nb_[a-z0-9_]+)\b", prior, re.I)
        if m:
            cast_id = m.group(1).lower()

    resolved = cast_resolve.resolve_cast(str(cast_id or asked or ""))
    cast = resolved.get("character") if resolved.get("ok") is not False else None
    loras = cast_resolve.loras_for_comfy(resolved) if cast else []

    # No readable prompt → approximate pixels (user loads, phone shots, etc.)
    if not prior:
        if not path_hint:
            return "I found the image but can't read a path to approximate it."
        # Optional VLM caption on Windows for richer i2i when PNG has no workflow
        vlm = _orla_action(
            cfg,
            {"action": "describe_image", "path": path_hint, "mode": "tags"},
            timeout=120,
        )
        caption = ""
        if vlm.get("ok"):
            caption = str(vlm.get("description") or "").strip()
        adjust_use = adjust or caption or "keep composition, enhance detail"
        log.info("Recreate → img2img approximate (no prompt) %s", path_hint)
        return approximate_via_img2img(
            cfg,
            source_path=path_hint,
            adjust_text=adjust_use,
            quality="gold_standard",
        )

    q_name = "gold_standard"
    use_locks = list(locks or [])
    prompt = prior
    if adjust:
        prompt = f"{prior.rstrip(', ')}, {adjust}"
    if cast and cast.get("trigger"):
        prompt = _ensure_trigger(prompt, str(cast["trigger"]))

    # Pose lock → OpenPose ControlNet (default) or img2img
    if path_hint and "pose" in use_locks:
        try:
            from . import agent_pulse

            agent_pulse.set_status(
                "nari", "generating", detail=f"Recreate · {mode} pose lock"
            )
        except Exception:
            pass
        if mode == "img2img":
            log.info("Recreate → img2img pose lock %s", path_hint)
            return approximate_via_img2img(
                cfg,
                source_path=path_hint,
                adjust_text=f"{prompt[:320]}. {adjust}".strip(". "),
                quality=q_name,
                denoise=float(gen.get("recreate_denoise", 0.42)),
            )
        log.info("Recreate → openpose pose lock %s", path_hint)
        return generate_via_openpose(
            cfg,
            source_path=path_hint,
            positive_prompt=prompt,
            loras=loras,
            cast=cast,
            quality=q_name,
            asked=asked or f"recreate {_src_name(path_hint)}",
        )

    # Scene-only lock without pose → mild img2img keeps layout better than soft English
    if path_hint and "scene" in use_locks:
        log.info("Recreate → img2img scene lock %s", path_hint)
        return approximate_via_img2img(
            cfg,
            source_path=path_hint,
            adjust_text=f"{prompt[:320]}. {adjust}".strip(". "),
            quality=q_name,
            denoise=float(gen.get("recreate_denoise", 0.42)),
        )

    desc = asked if asked and not asked.startswith("(from PNG)") else prior
    if adjust:
        desc = f"{desc}. Adjustment: {adjust}"
    if cast_id and str(cast_id).lower() not in desc.lower():
        desc = f"{cast_id}. {desc}"

    return generate(
        brain,
        desc,
        cfg,
        require_scene=True,
        scene_hint=adjust or prior,
        locks=use_locks,
        base_prompt=prior,
        quality=q_name,
    )


def cast_swap(
    brain,
    cfg: dict,
    *,
    character: str,
    selector: str = "last_displayed",
    locks: list[str] | None = None,
) -> str:
    """Keep pose/scene from stage1; change character via OpenPose or img2img."""
    src = resolve_source_meta(cfg, selector)
    if not src.get("ok"):
        return str(src.get("error") or "I couldn't find the stage-one image.")
    meta = src.get("meta") or {}
    path_hint = str(src.get("path") or "")
    prior = str(meta.get("expanded_prompt") or meta.get("asked") or "")
    if not looks_like_comfy_prompt(prior):
        prior = ""
    who = correct_stt_names(character)
    use_locks = list(locks or ["pose", "scene"])
    gen = cfg.get("generation") or {}
    mode = str(gen.get("cast_swap_mode") or "openpose").lower()

    resolved = cast_resolve.resolve_cast(who)
    if resolved.get("need_clarify"):
        return str(resolved.get("ask") or "Which character for the cast swap?")
    if resolved.get("ok") is False and resolved.get("error"):
        return str(resolved["error"])
    cast = resolved.get("character")
    if not cast:
        return (
            "I need a matched cast LoRA for cast swap. "
            "Name the character again — Frieren, Fern, Ubel, Park Heejin, and so on."
        )
    loras = cast_resolve.loras_for_comfy(resolved)
    # Cast swap needs a harder identity pull than a normal still
    if loras:
        loras = [dict(loras[0], weight=min(1.0, float(loras[0].get("weight", 0.8)) + 0.12))] + list(
            loras[1:]
        )
    prompt = _build_cast_swap_prompt(prior=prior, cast=cast)

    try:
        from . import agent_pulse

        agent_pulse.set_status(
            "nari", "generating", detail=f"Cast swap → {who} ({mode})"
        )
    except Exception:
        pass

    if not path_hint:
        # No pixels → last-resort prompt remix (should be rare)
        return generate(
            brain,
            f"{who}. {prompt}",
            cfg,
            require_scene=True,
            scene_hint=prompt,
            locks=use_locks,
            base_prompt=prompt,
            quality="gold_standard",
            require_cast=True,
        )

    if mode == "img2img":
        log.info("Cast swap → img2img %s → %s", path_hint, who)
        return approximate_via_img2img(
            cfg,
            source_path=path_hint,
            adjust_text=prompt,
            quality="gold_standard",
            denoise=float(gen.get("cast_swap_img2img_denoise", 0.58)),
            loras=loras,
            cast=cast,
        )

    log.info("Cast swap → openpose %s → %s", path_hint, who)
    # Slightly softer CN so LoRA/face can win over source silhouette cues
    old_strength = gen.get("openpose_strength")
    gen = dict(gen)
    gen["openpose_strength"] = float(gen.get("cast_swap_openpose_strength", 0.78))
    cfg_swap = dict(cfg)
    cfg_swap["generation"] = gen
    reply = generate_via_openpose(
        cfg_swap,
        source_path=path_hint,
        positive_prompt=prompt,
        loras=loras,
        cast=cast,
        quality="gold_standard",
        asked=f"cast swap {who} from {_src_name(path_hint)}",
    )
    if old_strength is not None:
        pass  # local gen copy only
    if "Done" in (reply or ""):
        reply += " Pose locked with OpenPose ControlNet."
    return reply


def cast_batch(
    brain,
    cfg: dict,
    *,
    show_id: str,
    selector: str = "last_displayed",
    locks: list[str] | None = None,
    cast_ids: list[str] | None = None,
) -> str:
    """Queue one still per cast member from a show, sharing stage1 OpenPose/i2i locks."""
    ids = list(cast_ids or cast_resolve.characters_for_show(show_id))
    if not ids:
        return f"No cast list for {show_id}."
    src = resolve_source_meta(cfg, selector)
    if not src.get("ok"):
        return str(src.get("error") or "I need a stage-one image first. Open one, then ask again.")
    batch_id = str(uuid.uuid4())[:8]
    chars, _ = cast_resolve._load()  # noqa: SLF001
    results: list[str] = []
    total = len(ids)
    for i, cid in enumerate(ids, start=1):
        ch = next((c for c in chars if c.get("id") == cid), None)
        name = (ch or {}).get("display_name") or cid
        try:
            from . import agent_pulse

            agent_pulse.set_status(
                "nari", "generating", detail=f"Cast batch {i}/{total} · {name}"
            )
        except Exception:
            pass
        notify_orla_job(
            cfg, event="queued", cast_id=cid, batch_id=batch_id
        )
        msg = cast_swap(
            brain,
            cfg,
            character=name,
            selector=selector,
            locks=locks,
        )
        results.append(f"{i}. {name}: {msg}")
        if "can't reach" in (msg or "").lower() or "rejected" in (msg or "").lower():
            break
    try:
        from . import agent_pulse

        agent_pulse.set_status("nari", "ready", detail=f"Batch {batch_id} done")
    except Exception:
        pass
    notify_orla_job(cfg, event="done", batch_id=batch_id)
    return (
        f"Queued cast batch {batch_id} for {show_id}: {total} stills. "
        f"First result: {results[0] if results else 'none'}."
    )

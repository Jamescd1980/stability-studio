#!/usr/bin/env python3
"""Forge Stage1 → mild img2img gold finish WITHOUT OpenPose.

Goal: keep vulva/labia/fingering detail while picking up eyes/detailer look.
Fails get recycled; keepers go beside forge as wan_start candidate.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stability-studio-mcp" / "scripts" / "general"))
from recycle_path import recycle  # noqa: E402

COMFY = "http://192.168.50.57:8188"
ORLA = "http://127.0.0.1:11436"
FORGE = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\_refined\scene_packs\01_tease\01_Frieren_Stage1_forge.png"
)
OUT_DIR = FORGE.parent
CAND_DIR = OUT_DIR / "_anatomy_candidates"

CKPT = "waijfu_alpha.safetensors"
WIDTH, HEIGHT = 832, 1472
STEPS, CFG = 36, 6.5
FRIEREN_LORA = "Frieren/Frieren.safetensors"
# No Eyes LoRA — it mush/melts an already-good forge face at even mild denoise.
GOLD = [
    ("ILDetailerV2.safetensors", 0.40),
]

PROMPT = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "newest, highres, ultra-detailed, anime++, bold outline, cel-shaded coloring, "
    "same face as source, keep Frieren face, clear teal-green eyes, sharp pupils, "
    "clean mouth, full lips, soft closed mouth, serene expression, "
    "soft daylight bedroom, white sheets, wooden headboard, window light, "
    "nb_frieren, Frieren, 1girl, solo, elf, pointy ears, "
    "long white hair, twintails, pale skin, small breasts, naked, "
    "sitting on bed, legs spread, looking at viewer, "
    "same pose as source, keep hand positions, "
    "right hand fondling her breast, left hand between her legs fingering her pussy, "
    "two fingers inserted in pussy, fingers parting labia, detailed vulva, "
    "detailed labia, wet pussy, visible pussy folds, explicit pussy, uncensored, "
    "do not move her left hand onto the bedsheets"
)

NEG = (
    "worst quality, low quality, bad quality, lowres, blurry, jpeg artifacts, "
    "sketch, censored, mosaic censoring, bar censor, "
    "barbie doll, featureless crotch, smooth crotch, no pussy, closed legs, "
    "hand on sheets only, empty crotch, plastic skin, "
    "melted face, deformed face, asymmetric eyes, crossed eyes, "
    "blob mouth, smudge mouth, open mouth mess, tongue out, ahegao, "
    "wrong face, different face, face warp, "
    "lens flare, light leak, prism light, rainbow light, sparkle, glitter, "
    "halo, glowing aura, bloom, chromatic aberration, "
    "blonde hair, yellow eyes, brown hair, black hair, watermark, signature, text, "
    "bad anatomy, bad hands, extra fingers, cum, semen"
)

# Very mild — polish only; face+hands+crotch must stay forge-true
VARIANTS = [
    (0.12, "d012"),
    (0.16, "d016"),
    (0.20, "d020"),
]


def upload(path: Path) -> str:
    data = path.read_bytes()
    boundary = f"----Ana{uuid.uuid4().hex}"
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode()
        + data
        + b"\r\n"
        + (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
            f"true\r\n"
        ).encode()
        + f"--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        f"{COMFY}/upload/image",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        up = json.loads(r.read().decode())
    return str(up.get("name") or path.name)


def build_wf(remote: str, denoise: float) -> dict:
    wf: dict = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CKPT},
        },
        "10": {"class_type": "LoadImage", "inputs": {"image": remote}},
        "12": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["10", 0],
                "upscale_method": "lanczos",
                "width": WIDTH,
                "height": HEIGHT,
                "crop": "disabled",
            },
        },
        "11": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["12", 0], "vae": ["4", 2]},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": PROMPT, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEG, "clip": ["4", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": uuid.uuid4().int % (2**32),
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": denoise,
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
            "inputs": {
                "filename_prefix": "frieren_s1_anatomy",
                "images": ["8", 0],
            },
        },
    }
    model_ref: list = ["4", 0]
    clip_ref: list = ["4", 1]
    nid = 20
    for name, w in [(FRIEREN_LORA, 0.9)] + GOLD:
        sid = str(nid)
        wf[sid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": name,
                "strength_model": w,
                "strength_clip": w,
                "model": model_ref,
                "clip": clip_ref,
            },
        }
        model_ref, clip_ref = [sid, 0], [sid, 1]
        nid += 1
    wf["3"]["inputs"]["model"] = model_ref
    wf["6"]["inputs"]["clip"] = clip_ref
    wf["7"]["inputs"]["clip"] = clip_ref
    return wf


def queue_and_wait(wf: dict, timeout_s: float = 360) -> str | None:
    r = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": wf, "client_id": str(uuid.uuid4())},
        timeout=30,
    )
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        h = requests.get(f"{COMFY}/history/{pid}", timeout=15).json()
        if pid not in h:
            time.sleep(1.5)
            continue
        for node in (h[pid].get("outputs") or {}).values():
            for im in node.get("images") or []:
                if im.get("filename"):
                    return str(im["filename"])
        if (h[pid].get("status") or {}).get("status_str") == "error":
            return None
        time.sleep(1.5)
    return None


def download(filename: str, dest: Path) -> None:
    qs = urllib.parse.urlencode(
        {"filename": filename, "subfolder": "", "type": "output"}
    )
    with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=120) as r:
        dest.write_bytes(r.read())


def vlm_gate(path: Path) -> tuple[bool, str]:
    q = (
        "Line 1 must be exactly PASS or FAIL. "
        "PASS only if ALL: (A) clean Frieren-like face no melt/blob mouth, "
        "(B) detailed vulva/labia visible, (C) fingers on/in the pussy. "
        "FAIL if fucked face, barbie crotch, or hand only on sheets. "
        "Line 2: one short reason."
    )
    body = {
        "action": "describe_image",
        "path": str(path),
        "mode": "desc",
        "prompt": q,
    }
    req = urllib.request.Request(
        f"{ORLA}/action",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    text = str(d.get("description") or d.get("error") or "")
    first = (text.strip().splitlines()[0] if text.strip() else "").strip().upper()
    ok = first == "PASS" or first.startswith("PASS ")
    if first.startswith("FAIL"):
        ok = False
    return ok, text


def main() -> int:
    if not FORGE.is_file():
        print("Missing forge:", FORGE)
        return 2
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    # Clear prior candidates
    for old in CAND_DIR.glob("*.png"):
        recycle(old)
    remote = upload(FORGE)
    print("source", FORGE.name, "uploaded", remote)

    keepers: list[Path] = []
    for denoise, tag in VARIANTS:
        print(f"\n=== img2img denoise={denoise} ({tag}) ===")
        name = queue_and_wait(build_wf(remote, denoise))
        if not name:
            print("  FAIL queue")
            continue
        dest = CAND_DIR / f"s1_anatomy_{tag}.png"
        download(name, dest)
        ok, desc = vlm_gate(dest)
        print("  VLM:", "PASS" if ok else "FAIL")
        print(" ", desc[:400].replace("\n", " | "))
        if ok:
            keepers.append(dest)
        else:
            recycle(dest)
            print("  recycled fail")

    final = OUT_DIR / "01_Frieren_Stage1_wan_start.png"
    if final.is_file():
        recycle(final)

    if not keepers:
        # Gold polish keeps wrecking face — use forge as Wan start.
        final.write_bytes(FORGE.read_bytes())
        for p in CAND_DIR.glob("*.png"):
            recycle(p)
        try:
            CAND_DIR.rmdir()
        except OSError:
            pass
        print("\nNo polish keepers — copied FORGE ->", final)
        return 0

    # Promote lowest denoise keeper (closest to forge); junk the rest
    keepers.sort(key=lambda p: p.name)
    best = keepers[0]
    final.write_bytes(best.read_bytes())
    for p in CAND_DIR.glob("*.png"):
        recycle(p)
    try:
        CAND_DIR.rmdir()
    except OSError:
        pass

    print("\nKEEPER ->", final)
    ok2, desc2 = vlm_gate(final)
    print("recheck", "PASS" if ok2 else "FAIL", desc2[:300])
    if not ok2:
        recycle(final)
        final.write_bytes(FORGE.read_bytes())
        print("recheck failed — fell back to FORGE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

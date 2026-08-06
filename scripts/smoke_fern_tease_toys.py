#!/usr/bin/env python3
"""Redo Fern tease stages 2+3 with mandatory typed dildo; solo negatives."""
from __future__ import annotations

import json
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

import requests

COMFY = "http://192.168.50.57:8188"
OUT = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\_refined\scene_packs\_fern_gold_smoke\tease_candidates"
)
REVIEW = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\_refined\scene_packs\_fern_gold_smoke\tease_review"
)

CKPT = "waijfu_alpha.safetensors"
WIDTH, HEIGHT = 832, 1472
STEPS, CFG = 36, 6.5
FERN_LORA = "Fern/Fern.safetensors"
# No LensFlare — sparkly halo wrecks stills
GOLD = [
    ("Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", 0.75),
    ("ILDetailerV2.safetensors", 0.65),
]

SCENES = [
    (
        "04_dp_rear_lookback",
        "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
        "newest, highres, ultra-detailed, bright bedroom, wooden floor, white rug, "
        "bed in background, window with curtains, soft daylight, perfect eyes, "
        "eye focus, anime++, bold outline, cel-shaded coloring, from behind, "
        "looking back over her shoulder at viewer, 1girl, solo, nb_fern, Fern, "
        "long purple hair, purple eyes, bangs, naked, on her hands and knees, "
        "ass up, double penetration with two thick purple dildos, one thick purple "
        "dildo deep in her pussy, one thick purple dildo deep in her ass, "
        "anal insertion, vaginal insertion, both dildos clearly visible stretching "
        "her holes, fucking herself with two dildos, masturbation, flushed cheeks, "
        "mouth open, look of pleasure",
    ),
]

NEG = (
    "worst quality, low quality, bad quality, lowres, blurry, jpeg artifacts, "
    "sketch, censored, watermark, signature, text, bad anatomy, bad hands, "
    "extra fingers, plastic skin, camera, dslr, camcorder, lens, smartphone, "
    "blonde hair, yellow eyes, white hair, elf ears, nb_frieren, Frieren, "
    "cum, semen, excessive bodily fluids, "
    "extra people, multiple girls, 2girls, 1boy, 2boys, multiple boys, "
    "man, male, male hand, male arm, disembodied hand, another person, "
    "couple, hetero, penis, cock, pov hand, grabbing from behind, "
    "no dildo, empty hands only, fingering only, "
    "lens flare, light leak, prism light, rainbow light, sparkle, glitter, "
    "halo, glowing aura, bloom, chromatic aberration"
)


def build_wf(prompt: str) -> dict:
    wf: dict = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": uuid.uuid4().int % (2**32),
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "fern_toy", "images": ["8", 0]},
        },
    }
    model_ref: list = ["4", 0]
    clip_ref: list = ["4", 1]
    nid = 20
    for name, w in [(FERN_LORA, 0.9)] + GOLD:
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


def queue_and_wait(wf: dict) -> str | None:
    r = requests.post(
        f"{COMFY}/prompt",
        json={"prompt": wf, "client_id": str(uuid.uuid4())},
        timeout=30,
    )
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < 360:
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
    qs = urllib.parse.urlencode({"filename": filename, "subfolder": "", "type": "output"})
    with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=120) as r:
        dest.write_bytes(r.read())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    results = []
    for stem, prompt in SCENES:
        print(f"=== {stem} ===")
        name = queue_and_wait(build_wf(prompt))
        if not name:
            print("FAIL")
            results.append((stem, None))
            continue
        dest = OUT / f"{stem}.png"
        download(name, dest)
        print(f"-> {dest} ({dest.stat().st_size // 1024} KB)")
        results.append((stem, dest))
        with (OUT / "_log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"stem": stem, "comfy": name, "prompt": prompt}) + "\n")
    print("Done candidates:", results)
    return 0 if all(p for _, p in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())

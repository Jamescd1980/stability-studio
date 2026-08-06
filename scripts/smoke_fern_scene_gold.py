#!/usr/bin/env python3
"""Smoke one scene pack as Fern + gold standard, NO ControlNet/OpenPose.

Variety + stronger BG from Invoke-style description prompts.
Usage:
  py -3 scripts/smoke_fern_scene_gold.py --pack tease
  py -3 scripts/smoke_fern_scene_gold.py --pack cowgirl
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

import requests

COMFY = "http://192.168.50.57:8188"
PACKS_ROOT = Path(
    r"D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens"
    r"\_refined\scene_packs"
)
OUT_ROOT = PACKS_ROOT / "_fern_gold_smoke"

CKPT = "waijfu_alpha.safetensors"
WIDTH, HEIGHT = 832, 1472
STEPS, CFG = 36, 6.5

FERN_LORA = "Fern/Fern.safetensors"
FERN_WEIGHT = 0.9
# No LensFlare — sparkly halo / light-leak wrecks bedroom stills
GOLD_LORAS = [
    ("Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", 0.75),
    ("ILDetailerV2.safetensors", 0.65),
]

# Scene briefs — Invoke layered style, Fern identity, NO pose ControlNet
PACK_SCENES: dict[str, list[tuple[str, str]]] = {
    "tease": [
        (
            "01_tease_stage1",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, soft warm daylight, bedroom, "
            "white sheets, wooden headboard, window with sheer curtains, "
            "hardwood floor, perfect eyes, eye focus, anime++, bold outline, "
            "cel-shaded coloring, looking at viewer, 1girl, solo, nb_fern, Fern, "
            "long purple hair, purple eyes, bangs, pale skin, naked, sitting on the "
            "edge of the bed, one hand fondling her breast, one hand fingering her "
            "pussy, blushing, slight smile, wet pussy",
        ),
        (
            "02_tease_stage2",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, soft daylight bedroom, rumpled white "
            "sheets, pillows, window light, nightstand with lamp, perfect eyes, "
            "anime++, bold outline, cel-shaded coloring, looking at viewer, "
            "1girl, solo, nb_fern, Fern, long purple hair, purple eyes, "
            "naked, kneeling on the bed, legs spread, both hands spreading her "
            "pussy, fingering her pussy, flushed cheeks, horny expression",
        ),
        (
            "03_tease_stage3",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, bright bedroom, wooden floor, white rug, "
            "bed in background, window with curtains, soft daylight, perfect eyes, "
            "anime++, bold outline, cel-shaded coloring, from behind, looking back "
            "over her shoulder, 1girl, solo, nb_fern, Fern, long purple hair, "
            "purple eyes, naked, on her hands and knees, ass up, inserting a thick "
            "purple dildo into her pussy, fucking herself with a dildo",
        ),
        (
            "04_tease_stage4",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, bedroom soft side light, dark wood "
            "furniture, green curtains, bed centered, perfect eyes, anime++, bold "
            "outline, cel-shaded coloring, looking at viewer, 1girl, solo, "
            "nb_fern, Fern, long purple hair, purple eyes, naked, on her back on the "
            "bed, legs spread toward viewer, fingering her pussy, mouth open, "
            "look of pleasure",
        ),
    ],
    "cowgirl": [
        (
            "01_cowgirl_preinsert",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, bedroom soft daylight, white sheets, "
            "wooden headboard, window light, perfect eyes, eye focus, anime++, "
            "bold outline, cel-shaded coloring, View from mans POV, solo focus, "
            "1girl, 1boy, nb_fern, Fern, long purple hair, purple eyes, naked, "
            "straddling a naked man lying on his back, cowgirl position, she grips "
            "his huge thick erect cock in her hand, large penis, thick shaft, "
            "veiny cock, oversized cock pressed against her pussy lips, about to "
            "sit down and insert, man under her, hetero, flushed cheeks",
        ),
        (
            "02_cowgirl_ride",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, bedroom soft daylight, white sheets, "
            "window light, plant by window, perfect eyes, eye focus, anime++, "
            "bold outline, cel-shaded coloring, View from mans POV, solo focus, "
            "1girl, 1boy, nb_fern, Fern, long purple hair, purple eyes, naked, "
            "cowgirl, riding cock, straddling man, vaginal penetration, vaginal sex, "
            "his cock deep in her pussy, hands on his chest, looking at viewer, "
            "flushed cheeks, look of pleasure, hetero",
        ),
    ],
    "missionary": [
        (
            "01_missionary",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, bedroom soft daylight, white sheets, "
            "perfect eyes, anime++, bold outline, cel-shaded coloring, looking at "
            "viewer, 1girl, nb_fern, Fern, long purple hair, purple eyes, naked, "
            "missionary, on her back, legs open, man between her legs fucking her "
            "pussy, vaginal penetration, vaginal sex, holding her thighs",
        ),
    ],
    "rear": [
        (
            "01_rear_lookback",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, night time bedroom, dark hardwood "
            "floors, dark green curtains, bed centered, window on right, soft "
            "lighting, perfect eyes, anime++, bold outline, cel-shaded coloring, "
            "View from mans POV, solo focus, 1girl, nb_fern, Fern, long purple "
            "hair, purple eyes, naked, flushed cheeks, mouth open looking back "
            "over her shoulder, on her hands and knees, legs slightly spread, "
            "man behind her shoving his cock in her pussy, man grabs her hips, "
            "doggystyle, vaginal penetration",
        ),
    ],
    "oral": [
        (
            "01_oral",
            "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
            "newest, highres, ultra-detailed, bedroom soft lighting, bed edge, "
            "perfect eyes, anime++, bold outline, cel-shaded coloring, View from "
            "mans POV, solo focus, 1girl, nb_fern, Fern, long purple hair, purple "
            "eyes, naked, sitting on the edge of the bed, a naked man standing in "
            "front of her, Fern leans in and sucks the mans cock, blowjob, "
            "deepthroat, small erect nipples, full lips",
        ),
    ],
}

NEG_BASE = (
    "worst quality, low quality, bad quality, lowres, blurry, jpeg artifacts, "
    "sketch, censored, watermark, signature, text, bad anatomy, bad hands, "
    "extra fingers, plastic skin, camera, dslr, camcorder, lens, smartphone, "
    "blonde hair, yellow eyes, white hair, elf ears, nb_frieren, Frieren, "
    "cum, semen, excessive bodily fluids, "
    "lens flare, light leak, prism light, rainbow light, sparkle, glitter, "
    "halo, glowing aura, bloom, chromatic aberration"
)
# Solo packs: block partner leak (man's hand/arm)
NEG_SOLO = (
    NEG_BASE
    + ", extra people, multiple girls, 2girls, 1boy, 2boys, multiple boys, "
    "man, male, male hand, male arm, disembodied hand, another person, "
    "couple, hetero, penis, cock, pov hand, grabbing from behind"
)
# Couple 1girl+1boy: block gangbang / DP extras
NEG_COUPLE = (
    NEG_BASE
    + ", 2girls, multiple girls, 2boys, 3boys, multiple boys, gangbang, "
    "group sex, double penetration, two penises, three penises, "
    "disembodied penis, floating penis"
)
SOLO_PACKS = {"tease"}  # masturbation / dildo — no partner


def build_wf(prompt: str, *, solo: bool = False, couple: bool = False) -> dict:
    if solo:
        neg = NEG_SOLO
    elif couple:
        neg = NEG_COUPLE
    else:
        neg = NEG_BASE
    wf: dict = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CKPT},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": neg, "clip": ["4", 1]},
        },
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
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "fern_gold", "images": ["8", 0]},
        },
    }
    model_ref: list = ["4", 0]
    clip_ref: list = ["4", 1]
    nid = 20
    for name, weight in [(FERN_LORA, FERN_WEIGHT)] + GOLD_LORAS:
        sid = str(nid)
        wf[sid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": name,
                "strength_model": weight,
                "strength_clip": weight,
                "model": model_ref,
                "clip": clip_ref,
            },
        }
        model_ref = [sid, 0]
        clip_ref = [sid, 1]
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
            print("  comfy error", (h[pid].get("status") or {}).get("messages"))
            return None
        time.sleep(1.5)
    return None


def download(filename: str, dest: Path) -> None:
    qs = urllib.parse.urlencode(
        {"filename": filename, "subfolder": "", "type": "output"}
    )
    with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=120) as r:
        dest.write_bytes(r.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--pack",
        default="tease",
        choices=sorted(PACK_SCENES.keys()),
        help="Scene group to smoke",
    )
    ap.add_argument(
        "--only",
        default="",
        help="Comma-separated stem prefixes to run (e.g. 01_cowgirl_preinsert)",
    )
    args = ap.parse_args()
    scenes = PACK_SCENES[args.pack]
    if args.only.strip():
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        scenes = [(stem, p) for stem, p in scenes if stem in want]
        if not scenes:
            print(f"No scenes matched --only {want!r}")
            return 2
    out = OUT_ROOT / f"01_{args.pack}" if args.pack == "tease" else OUT_ROOT / args.pack
    # stable names
    out = OUT_ROOT / args.pack
    out.mkdir(parents=True, exist_ok=True)
    print(f"Fern gold smoke pack={args.pack} n={len(scenes)} -> {out}")
    print("No OpenPose / ControlNet (txt2img variety + BG)")
    results = []
    for stem, prompt in scenes:
        print(f"\n=== {stem} ===")
        print("  ", prompt[:140], "...")
        name = queue_and_wait(
            build_wf(
                prompt,
                solo=args.pack in SOLO_PACKS,
                couple=args.pack not in SOLO_PACKS,
            )
        )
        if not name:
            print("  FAIL")
            results.append((stem, None))
            continue
        dest = out / f"{stem}_fern_gold.png"
        download(name, dest)
        with (out / "_batch_log.jsonl").open("a", encoding="utf-8") as f:
            f.write(
                json.dumps({"stem": stem, "comfy": name, "dest": dest.name, "prompt": prompt})
                + "\n"
            )
        print(f"  -> {dest.name} ({dest.stat().st_size // 1024} KB)")
        results.append((stem, dest.name))
    ok = sum(1 for _, d in results if d)
    print(f"\nDone {ok}/{len(results)} -> {out}")
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())

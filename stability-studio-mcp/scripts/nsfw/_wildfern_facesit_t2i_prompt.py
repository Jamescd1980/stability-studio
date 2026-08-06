"""Facesit t2i — exact v3 keeper line; only BG swap to dark wood / white sheets / city."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests

FORGE = "http://127.0.0.1:7860"
CKPT = "waijfu_alpha.safetensors"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften\_bgcity_i2i\_finish"
)
# Keeper seed first, then nearby probes
SEEDS = (59121, 59131, 59141, 59151)
W, H = 1024, 1152

# facesit_darkness_pov_v3 body — only loft materials swapped to pack lock
# (pale wood/purple sheets → dark wood grain / white sheets / headboard right)
PROMPT_BODY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
    "loft bedroom at night, warm dark brown vertical wood panel walls, "
    "wood grain planks, dark grooves between planks, "
    "two framed pictures on wall, cream bedside lamps, wooden window, "
    "night sky city skyline, white sheets, "
    "dark wood bed headboard on the right of the frame, warm lamp light, "
    "low angle looking up, facesitting, solo focus, 1girl, "
    "nb_fern, Fern, purple hair, purple eyes, completely nude, large breasts, "
    "pussy on face, looking down at viewer, pleasure face, "
    "blonde bangs, blue eyes looking up at bottom edge, wet pussy, cunnilingus"
)

# Exact v3 negative + pale/purple wall/sheet fights from city batch
NEG = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "man, male, penis, cock, 1boy, "
    "cum, semen, male cum, white stains, white splatters, "
    "bukkake, aftersex, fluids, fluid, "
    "pine trees, trees outside window, forest, evergreen, "
    "camera, dslr, daytime, clothes, lingerie, pubic hair, "
    "small breasts, flat chest, "
    "blonde on top, blue eyes on Fern, purple eyes under, "
    "purple bangs under, black hair under, two Ferns, "
    "closed eyes, eyes closed, "
    "purple walls, lavender walls, pink walls, pale wood, yellow walls, "
    "purple sheets, lavender sheets, pink sheets"
)
FACE_W = 0.55


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    raise RuntimeError(f"no Facesitting LoRA: {sorted(names)}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = face_tag()
    prompt = f"<lora:{face}:{FACE_W}> <lora:Fern_id_v1:0.9> {PROMPT_BODY}"
    print("=== facesit t2i v3 keeper line + city wood BG ===", flush=True)
    print("POS", prompt, flush=True)
    print("NEG", NEG, flush=True)
    for seed in SEEDS:
        payload = {
            "prompt": prompt,
            "negative_prompt": NEG,
            "steps": 32,
            "cfg_scale": 6.0,
            "width": W,
            "height": H,
            "seed": seed,
            "sampler_name": "Euler a",
            "restore_faces": False,
            "override_settings": {"sd_model_checkpoint": CKPT},
            "override_settings_restore_afterwards": True,
            "alwayson_scripts": {"ADetailer": {"args": [False]}},
        }
        print(f"seed {seed}", flush=True)
        r = requests.post(f"{FORGE}/sdapi/v1/txt2img", json=payload, timeout=1800)
        r.raise_for_status()
        dest = OUT / f"facesit_v3line_s{seed}.png"
        dest.write_bytes(base64.b64decode(r.json()["images"][0].split(",", 1)[-1]))
        (OUT / f"{dest.stem}.json").write_text(
            json.dumps({"seed": seed, "prompt": prompt, "negative": NEG}, indent=2),
            encoding="utf-8",
        )
        print("  OK", dest.name, dest.stat().st_size, flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Facesit BG swap — img2img from keeper v3; hard wood/city lock (pose from init)."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
CKPT = "waijfu_alpha.safetensors"
SRC = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften\facesit_darkness_pov_v3.png"
)
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften\_bgcity_i2i\_finish"
)
SEED = 62847
# Prior 0.30–0.50 left painted/purple walls — push BG harder
DENOISES = (0.45, 0.55, 0.62)

QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)
# Front-load wood/city so BG wins token budget vs act
BG = (
    "loft bedroom at night in town, "
    "warm dark brown vertical wood panel walls, wood grain planks, "
    "dark grooves between planks, wooden wall panels, timber walls, "
    "cream conical lampshade with warm yellow glow, dark ornate lamp base on dark wood nightstand, "
    "small dark framed picture on wall, "
    "wooden window showing night city skyline with lit skyscrapers, distant city lights, "
    "urban night view, no trees, "
    "white rumpled bed sheets, white pillows, "
    "dark wood bed headboard on the right of the frame, "
    "warm low key lamp light, soft shadows, "
)
ACT = (
    "low angle looking up, facesitting, solo focus, 1girl, "
    "nb_fern, Fern, purple hair, purple eyes, completely nude, large breasts, "
    "pussy on face, looking down at viewer, pleasure face, "
    "blonde bangs, blue eyes looking up at bottom edge, wet pussy, cunnilingus"
)
NEG = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "painted wall, flat wall, plaster wall, drywall, smooth wall, "
    "purple walls, lavender walls, pink walls, blue walls, teal walls, "
    "pale wood, yellow walls, cream walls, beige walls, "
    "purple sheets, lavender sheets, pink sheets, "
    "pine trees, trees outside window, forest, evergreen, woods, rural, cabin, "
    "man, male, male face, male head, man's face, short hair under, "
    "black hair under, brown hair under, dark hair under, "
    "1boy, penis, cock, "
    "blonde on top, purple hair under, two Ferns, 2girls, "
    "cum, semen, white stains, white splatters, bukkake, aftersex, "
    "camera, dslr, camcorder, daytime, neon, clothes, lingerie, pubic hair, "
    "closed eyes, eyes closed"
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
    if not SRC.is_file():
        print("MISSING", SRC, flush=True)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = face_tag()
    prompt = (
        f"<lora:{face}:{FACE_W}> <lora:Fern_id_v1:0.9> "
        f"{QUALITY}{BG}{ACT}"
    )
    with Image.open(SRC) as im:
        w, h = im.size
        rgb = im.convert("RGB")
    rgb_path = OUT / "_facesit_v3_rgb.png"
    rgb.save(rgb_path, format="PNG")
    init_b64 = base64.b64encode(rgb_path.read_bytes()).decode()

    print("=== facesit i2i v3 hard BG (d45/d55/d62) ===", flush=True)
    print("SRC", SRC, flush=True)
    print("POS", prompt, flush=True)
    for d in DENOISES:
        tag = f"facesit_i2i_bghard_d{int(d * 100):02d}"
        print(f"{tag} denoise={d}", flush=True)
        payload = {
            "init_images": [init_b64],
            "prompt": prompt,
            "negative_prompt": NEG,
            "denoising_strength": d,
            "steps": 32,
            "cfg_scale": 6.5,
            "width": w,
            "height": h,
            "seed": SEED,
            "sampler_name": "Euler a",
            "restore_faces": False,
            "override_settings": {"sd_model_checkpoint": CKPT},
            "override_settings_restore_afterwards": True,
            "alwayson_scripts": {"ADetailer": {"args": [False]}},
        }
        r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
        r.raise_for_status()
        dest = OUT / f"{tag}.png"
        dest.write_bytes(base64.b64decode(r.json()["images"][0].split(",", 1)[-1]))
        (OUT / f"{tag}.json").write_text(
            json.dumps(
                {"src": str(SRC), "seed": SEED, "denoise": d, "prompt": prompt, "negative": NEG},
                indent=2,
            ),
            encoding="utf-8",
        )
        print("  OK", dest.name, dest.stat().st_size, flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

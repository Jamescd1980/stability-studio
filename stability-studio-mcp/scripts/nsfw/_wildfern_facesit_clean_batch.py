"""Clean facesit batch — no img2img stack. Short Invoke-style prompts.

Mistakes we were making:
- img2img 0.45–0.62 on drifted seeds → mush, purple walls, semen stains, eye swap
- essay prompts + Eyes LoRA + high Facesitting (Pony) fighting waijfu
- BG war (lavender vs dark wood) while keepers use pale wood plank loft

This run:
- POV: fresh txt2img, short prompt, Facesitting ~0.55, no Eyes LoRA
- Reverse: mild img2img from Fern_Facesit_v10 @ denoise 0.32–0.38 only
- Fluids: wet pussy / pussy juice only; hard-negate cum/semen/white stains
- Eyes: purple on Fern, blue on Darkness fringe; negate swap
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
REV_INIT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\Approved\Fern_Facesit_v10.png"
)
CKPT = "waijfu_alpha.safetensors"

# Match keeper loft (Facesit_v10 / forge_soften) — pale wood planks, not purple paint
LOFT = (
    "loft bedroom at night, pale wood plank walls, two framed pictures on wall, "
    "cream bedside lamps, wooden window, night sky with pine trees, "
    "purple sheets, warm lamp light, "
)
QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)

NEG = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "man, male, penis, cock, 1boy, "
    "cum, semen, male cum, white stains, white splatters, stains on wall, "
    "bukkake, aftersex, fluids, fluid, "
    "purple painted walls, magenta walls, neon purple room, "
    "small breasts, flat chest, "
    "camera, dslr, daytime, clothes, lingerie, pubic hair"
)
NEG_POV = (
    NEG
    + ", blonde on top, "
    "blue eyes on Fern, blue eyes looking down, "
    "purple eyes under, purple eyes looking up, "
    "purple bangs under, black hair under, two Ferns, "
    "closed eyes, eyes closed"
)
NEG_REV = (
    NEG
    + ", blonde on top, blonde ass, "
    "looking back, looking over shoulder, looking at viewer, "
    "Fern face, eyes looking at viewer, "
    "purple hair under"
)

AD_OFF = {"ADetailer": {"args": [False]}}


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    raise RuntimeError(f"no Facesitting LoRA: {sorted(names)}")


def txt2img(*, name: str, prompt: str, neg: str, seed: int, w: int, h: int) -> Path:
    out = OUT / f"{name}.png"
    payload = {
        "prompt": prompt,
        "negative_prompt": neg,
        "steps": 32,
        "cfg_scale": 6.0,
        "width": w,
        "height": h,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF,
    }
    print(f"=== TXT {name} seed={seed}", flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/txt2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    out.write_bytes(raw)
    (OUT / f"{name}.json").write_text(
        json.dumps({"name": name, "seed": seed, "mode": "txt2img", "prompt": prompt}, indent=2),
        encoding="utf-8",
    )
    print("OK", out, len(raw), flush=True)
    return out


def img2img(
    *,
    name: str,
    init: Path,
    prompt: str,
    neg: str,
    seed: int,
    denoise: float,
) -> Path:
    out = OUT / f"{name}.png"
    tmp = OUT / "_tmp_init"
    tmp.mkdir(exist_ok=True)
    rgb = tmp / f"{init.stem}_rgb.png"
    with Image.open(init) as im:
        im.convert("RGB").save(rgb, format="PNG")
    payload = {
        "init_images": [base64.b64encode(rgb.read_bytes()).decode()],
        "prompt": prompt,
        "negative_prompt": neg,
        "denoising_strength": denoise,
        "steps": 28,
        "cfg_scale": 5.5,
        "width": 1024,
        "height": 1024,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF,
    }
    print(f"=== I2I {name} d={denoise} seed={seed}", flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=1800)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    out.write_bytes(raw)
    (OUT / f"{name}.json").write_text(
        json.dumps(
            {
                "name": name,
                "seed": seed,
                "mode": "img2img",
                "denoise": denoise,
                "init": str(init),
                "prompt": prompt,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("OK", out, len(raw), flush=True)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not REV_INIT.is_file():
        raise FileNotFoundError(REV_INIT)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = face_tag()
    # Mild Facesitting — high weight + Eyes LoRA was wrecking finish/eyes
    lora = f"<lora:{face}:0.55> <lora:Fern_id_v1:0.88> "

    # --- Darkness POV: fresh txt2img ---
    pov = [
        dict(
            name="facesit_darkness_pov_v1",
            seed=57001,
            h=1024,
            prompt=(
                lora
                + QUALITY
                + LOFT
                + "View from below looking up, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair, purple eyes, "
                "completely nude, large breasts, "
                "sitting on a face, looking down at viewer, flushed cheeks, "
                "blonde bangs and blue eyes at bottom of frame, "
                "wet pussy, cunnilingus"
            ),
        ),
        dict(
            name="facesit_darkness_pov_v2",
            seed=57011,
            h=1024,
            prompt=(
                lora
                + QUALITY
                + LOFT
                + "View from below, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
                "completely nude, large breasts, "
                "straddling a face, looking down at viewer, mouth open, "
                "only blonde bangs and blue eyes under her pussy, "
                "wet pussy, pussy juice, cunnilingus"
            ),
        ),
        dict(
            name="facesit_darkness_pov_v3",
            seed=57021,
            h=1152,
            prompt=(
                lora
                + QUALITY
                + LOFT
                + "low angle looking up, facesitting, "
                "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
                "completely nude, large breasts, "
                "pussy on face, looking down at viewer, pleasure face, "
                "blonde bangs, blue eyes looking up at bottom edge, "
                "wet pussy, cunnilingus"
            ),
        ),
    ]
    for j in pov:
        txt2img(
            name=j["name"],
            prompt=j["prompt"],
            neg=NEG_POV,
            seed=j["seed"],
            w=1024,
            h=j["h"],
        )

    # --- Reverse: preserve Facesit_v10 quality; light edit only ---
    rev_base = (
        "<lora:Fern_id_v1:0.9> "
        + QUALITY
        + LOFT
        + "from behind, ass focus, "
        "solo focus, 1girl, nb_fern, Fern, long purple hair down bare back, "
        "completely nude, large breasts, bare ass, "
    )
    rev = [
        dict(
            name="facesit_reverse_ass_chin_v1",
            seed=57101,
            denoise=0.34,
            prompt=(
                rev_base
                + "head out of frame, faceless, "
                "sitting on blonde face, blonde chin sucking clit, "
                "wet pussy, cunnilingus"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v2",
            seed=57111,
            denoise=0.36,
            prompt=(
                rev_base
                + "face buried in pillows, head away, "
                "blonde chin and mouth under her pussy sucking clit, "
                "wet pussy, pussy juice, cunnilingus"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v3",
            seed=57121,
            denoise=0.32,
            prompt=(
                rev_base
                + "no face in frame, "
                "blonde jaw under pussy, lips on clit, "
                "wet pussy, cunnilingus"
            ),
        ),
    ]
    for j in rev:
        img2img(
            name=j["name"],
            init=REV_INIT,
            prompt=j["prompt"],
            neg=NEG_REV,
            seed=j["seed"],
            denoise=j["denoise"],
        )

    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

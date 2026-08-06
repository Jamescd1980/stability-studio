"""Reverse facesit — txt2img ONLY (no Facesit_v10 / no img2img).

Roles locked: Fern (purple) on Darkness (blonde chin). Camera from behind.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
CKPT = "waijfu_alpha.safetensors"

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
    "cum, semen, male cum, white stains, white splatters, "
    "bukkake, aftersex, fluids, fluid, "
    "blonde on top, blonde ass, blonde back, blonde looking back, "
    "looking back, looking over shoulder, looking at viewer, "
    "Fern face, face of top girl, eyes looking at viewer, portrait, "
    "purple hair under, side view, profile view, "
    "camera, dslr, daytime, clothes, lingerie, pubic hair, "
    "small breasts, flat chest"
)
AD_OFF = {"ADetailer": {"args": [False]}}


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    raise RuntimeError(f"no Facesitting LoRA: {sorted(names)}")


def txt2img(*, name: str, prompt: str, seed: int) -> Path:
    out = OUT / f"{name}.png"
    payload = {
        "prompt": prompt,
        "negative_prompt": NEG,
        "steps": 32,
        "cfg_scale": 6.0,
        "width": 1024,
        "height": 1024,
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
        json.dumps(
            {"name": name, "seed": seed, "mode": "txt2img", "prompt": prompt},
            indent=2,
        ),
        encoding="utf-8",
    )
    print("OK", out, len(raw), flush=True)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = face_tag()
    # Mild Facesitting — reverse is camera angle, not POV lookdown
    lora = f"<lora:{face}:0.5> <lora:Fern_id_v1:0.9> "

    jobs = [
        dict(
            name="facesit_reverse_ass_chin_v1",
            seed=58001,
            prompt=(
                lora
                + QUALITY
                + LOFT
                + "View from behind, ass focus, rear view, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair down bare back, "
                "completely nude, large breasts, bare ass, "
                "head out of frame, faceless, "
                "Fern sitting on a blonde face, "
                "blonde chin and mouth under her pussy sucking her clit, "
                "wet pussy, cunnilingus"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v2",
            seed=58011,
            prompt=(
                lora
                + QUALITY
                + LOFT
                + "from behind, ass focus, "
                "solo focus, 1girl, nb_fern, Fern, purple hair cascading down back, "
                "completely nude, large breasts, bare ass, "
                "face buried in pillows, head away from viewer, "
                "kneeling on blonde face, "
                "only blonde chin jaw and lips under her crotch sucking clit, "
                "wet pussy, pussy juice, cunnilingus"
            ),
        ),
        dict(
            name="facesit_reverse_ass_chin_v3",
            seed=58021,
            prompt=(
                lora
                + QUALITY
                + LOFT
                + "close rear view, ass focus, "
                "solo focus, 1girl, nb_fern, Fern, long purple hair, "
                "completely nude, large breasts, bare hips and ass, "
                "no face in frame, head cropped out, "
                "sitting on blonde face, blonde jaw under pussy, "
                "lips sucking clit, wet pussy, cunnilingus"
            ),
        ),
    ]
    for j in jobs:
        txt2img(name=j["name"], prompt=j["prompt"], seed=j["seed"])
    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

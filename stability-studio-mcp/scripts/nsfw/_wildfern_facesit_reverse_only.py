"""Reverse-cam facesit only — Fern ass + Darkness chin. No Facesitting LoRA (POV bias)."""
from __future__ import annotations

import base64
import json

import requests

FORGE = "http://127.0.0.1:7860"
from pathlib import Path

OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
CKPT = "waijfu_alpha.safetensors"
NIGHT = (
    "loft bedroom at night, dark wood panel walls, warm bedside lamp light, "
    "dark window night sky, purple sheets, "
)
Q = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)
LORA = "<lora:Fern_id_v1:0.95> "
NEG = (
    "bad quality, worst quality, blurry, bad anatomy, man, male, penis, cock, "
    "blonde on top, blonde ass, blonde back, looking back, looking over shoulder, "
    "looking at viewer, face, eyes, smile, open mouth face, portrait, "
    "purple hair under, Fern face, "
    "camera, dslr, daytime, clothes, lingerie, pubic hair"
)
AD = {"ADetailer": {"args": [False]}}
JOBS = [
    dict(
        name="facesit_reverse_ass_chin_v1",
        seed=54301,
        prompt=(
            LORA
            + Q
            + NIGHT
            + "ass focus, from behind, rear view, "
            "solo focus, 1girl, nb_fern, Fern, long purple hair down her bare back, "
            "completely nude, bare ass, head out of frame, faceless, "
            "kneeling on a bed over a face, pussy pressed to a mouth, "
            "blonde chin and mouth under her crotch sucking her clit, "
            "tongue on clit, cunnilingus, wet pussy"
        ),
    ),
    dict(
        name="facesit_reverse_ass_chin_v2",
        seed=54311,
        prompt=(
            LORA
            + Q
            + NIGHT
            + "ass focus, from behind, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, "
            "completely nude bare ass, upper body bent forward into pillows, "
            "face buried in sheets, "
            "pussy on blonde mouth below, "
            "only blonde chin and lips visible under her, sucking clit, cunnilingus"
        ),
    ),
    dict(
        name="facesit_reverse_ass_chin_v3",
        seed=54321,
        prompt=(
            LORA
            + Q
            + NIGHT
            + "close-up from behind, ass focus, "
            "solo focus, 1girl, nb_fern, Fern, purple hair cascading, "
            "completely nude, bare hips and ass, no face in frame, "
            "sitting on blonde face, blonde jaw under pussy, "
            "lips sucking clit, wet tongue, cunnilingus"
        ),
    ),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    for j in JOBS:
        print("===", j["name"], flush=True)
        r = requests.post(
            f"{FORGE}/sdapi/v1/txt2img",
            json={
                "prompt": j["prompt"],
                "negative_prompt": NEG,
                "steps": 36,
                "cfg_scale": 7,
                "width": 1024,
                "height": 1024,
                "seed": j["seed"],
                "sampler_name": "Euler a",
                "restore_faces": False,
                "override_settings": {"sd_model_checkpoint": CKPT},
                "alwayson_scripts": AD,
            },
            timeout=1800,
        ).json()
        raw = base64.b64decode(r["images"][0].split(",", 1)[-1])
        out = OUT / f"{j['name']}.png"
        out.write_bytes(raw)
        (OUT / f"{j['name']}.json").write_text(
            json.dumps({"job": j["name"], "seed": j["seed"], "prompt": j["prompt"]}, indent=2),
            encoding="utf-8",
        )
        print("OK", out, len(raw), flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

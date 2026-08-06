"""Wild Fern facesit replace — local Forge + Facesitting LoRA, ADetailer OFF.

LOCKED: Fern (purple) always sits on Darkness (blonde). Reverse = camera only.
No Darkness ID LoRA (it was flipping who sits). Blonde under = prompt-only.
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import requests

FORGE = "http://127.0.0.1:7860"
OUT = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\facesit_replace"
)
CKPT = "waijfu_alpha.safetensors"

NIGHT = (
    "loft bedroom at night, dark wood panel walls, warm bedside lamp light, "
    "dark window night sky, purple sheets, soft diffused lighting, "
)
QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, perfect eyes, "
)

# Fern + facesit + eyes only. Darkness ID LoRA flips her onto the top seat.
LORA = (
    "<lora:Facesitting:0.75> <lora:Fern_id_v1:0.92> "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.72> "
)
# Lower facesit LoRA on reverse — POV LoRA pushes look-down / lookback faces
LORA_REV = (
    "<lora:Facesitting:0.45> <lora:Fern_id_v1:0.95> "
)

NEG_POV = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "man, male, penis, cock, 1boy, hetero, "
    "blonde on top, blonde girl sitting, blonde breasts above, "
    "yellow hair on top, golden hair sitting, "
    "two Ferns, purple hair under, black hair under, dark bangs under, "
    "purple eyes under, purple fringe at bottom, "
    "closed eyes, eyes closed, sleeping, "
    "clothes, lingerie, bra, panties, "
    "camera, dslr, camcorder, lens, smartphone, "
    "daytime, bright daylight, pubic hair"
)
NEG_REV = (
    "bad quality, worst quality, blurry, bad anatomy, extra limbs, "
    "man, male, penis, cock, 1boy, hetero, "
    "blonde on top, blonde sitting, blonde ass, blonde back, blonde hair down back, "
    "looking back, looking over shoulder, looking at viewer, face looking back, "
    "yellow eyes, glowing eyes, top girl face visible, "
    "purple hair under, Fern face under, purple bangs under, "
    "clothes, lingerie, "
    "camera, dslr, camcorder, lens, "
    "daytime, bright daylight, pubic hair"
)

AD_OFF = {"ADetailer": {"args": [False]}}

JOBS = [
    dict(
        name="facesit_darkness_pov_v1",
        seed=54001,
        prompt=(
            LORA
            + QUALITY
            + NIGHT
            + "View from below looking up, facesitting, "
            "solo focus, 1girl, nb_fern, Fern, long purple hair, purple eyes, "
            "completely nude, fully naked, bare breasts, no clothes, "
            "Fern sitting on a face, thighs around a head, pussy on face, "
            "looking down at viewer, flushed cheeks, pleasure face, mouth slightly open, "
            "only at bottom edge of frame: blonde bangs and blue eyes looking up, "
            "blonde hair fringe under her pussy, blue eyes, "
            "not a second purple girl, wet pussy, cunnilingus"
        ),
        neg=NEG_POV,
        w=1024,
        h=1024,
    ),
    dict(
        name="facesit_darkness_pov_v2",
        seed=54011,
        prompt=(
            LORA
            + QUALITY
            + NIGHT
            + "from below looking up between thighs, facesitting, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, bare breasts, straddling a face, "
            "looking down at viewer with pleasure, open mouth, "
            "bottom of image shows blonde forehead bangs and blue eyes only, "
            "blonde under purple pussy, blue eyes looking up, "
            "purple hair only on the girl on top, wet pussy, cunnilingus"
        ),
        neg=NEG_POV,
        w=1024,
        h=1024,
    ),
    dict(
        name="facesit_darkness_pov_v3",
        seed=54021,
        prompt=(
            LORA
            + QUALITY
            + NIGHT
            + "low angle view looking up, facesitting, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, purple eyes, "
            "completely nude, bare breasts, sitting on a blonde face, "
            "looking down at viewer, flushed cheeks, "
            "viewer fringe: long blonde bangs, blue eyes looking up into her pussy, "
            "no purple hair at bottom of frame, wet pussy juice, cunnilingus"
        ),
        neg=NEG_POV,
        w=1024,
        h=1152,
    ),
    dict(
        name="facesit_reverse_ass_chin_v1",
        seed=54201,
        prompt=(
            LORA_REV
            + QUALITY
            + NIGHT
            + "View from behind, cropped above the shoulders, "
            "solo focus, 1girl, nb_fern, Fern, long purple hair down bare back, "
            "completely nude, bare ass, no face, head cropped out of frame, "
            "kneeling over a face, pussy on a blonde mouth, "
            "bottom of frame: blonde chin and lips sucking her clit, "
            "tongue on clit, cunnilingus, wet pussy, "
            "purple hair only on the girl whose ass is shown"
        ),
        neg=NEG_REV,
        w=1024,
        h=1024,
    ),
    dict(
        name="facesit_reverse_ass_chin_v2",
        seed=54211,
        prompt=(
            LORA_REV
            + QUALITY
            + NIGHT
            + "rear view close-up of purple-haired bare ass, "
            "solo focus, 1girl, nb_fern, Fern, purple hair, "
            "completely nude, faceless, head outside the frame, "
            "sitting on blonde face, "
            "only blonde chin jaw mouth under her crotch, "
            "sucking clit, licking clit, cunnilingus, "
            "no shoulder turn, no face of the girl on top"
        ),
        neg=NEG_REV,
        w=1024,
        h=1024,
    ),
    dict(
        name="facesit_reverse_ass_chin_v3",
        seed=54221,
        prompt=(
            LORA_REV
            + QUALITY
            + NIGHT
            + "from behind, focus on purple hair and bare ass, "
            "solo focus, 1girl, nb_fern, Fern, "
            "completely nude, ass toward viewer, upper body bent forward, "
            "face hidden in sheets, head down away from viewer, "
            "blonde chin under her pussy sucking clit, "
            "cunnilingus, wet tongue, "
            "purple hair girl on top, blonde under"
        ),
        neg=NEG_REV,
        w=1024,
        h=1024,
    ),
]


def wait_forge(timeout_s: int = 120) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if requests.get(f"{FORGE}/sdapi/v1/sd-models", timeout=5).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("Local Forge not up")


def resolve_face_lora_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    if "Facesitting" in names:
        return "Facesitting"
    if "povFacesitting" in names:
        return "povFacesitting"
    raise RuntimeError(f"Forge missing Facesitting LoRA; have={sorted(names)}")


def txt2img(job: dict) -> Path:
    out = OUT / f"{job['name']}.png"
    payload = {
        "prompt": job["prompt"],
        "negative_prompt": job["neg"],
        "steps": 34,
        "cfg_scale": 6.5,
        "width": job["w"],
        "height": job["h"],
        "seed": job["seed"],
        "sampler_name": "Euler a",
        "scheduler": "Automatic",
        "batch_size": 1,
        "n_iter": 1,
        "restore_faces": False,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": AD_OFF,
    }
    print("===", out.name, "seed", job["seed"], flush=True)
    r = requests.post(f"{FORGE}/sdapi/v1/txt2img", json=payload, timeout=1800)
    r.raise_for_status()
    data = r.json()
    imgs = data.get("images") or []
    if not imgs:
        raise RuntimeError(f"No images for {job['name']}: {data.keys()}")
    raw = base64.b64decode(imgs[0].split(",", 1)[-1])
    out.write_bytes(raw)
    info = data.get("info")
    if isinstance(info, str):
        try:
            info = json.loads(info)
        except json.JSONDecodeError:
            info = {"raw": info}
    (OUT / f"{job['name']}.json").write_text(
        json.dumps({"job": job["name"], "seed": job["seed"], "info": info}, indent=2),
        encoding="utf-8",
    )
    print("OK", out, len(raw), flush=True)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    wait_forge()
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    face = resolve_face_lora_tag()
    jobs = JOBS
    if face != "Facesitting":
        jobs = [
            {**j, "prompt": j["prompt"].replace("<lora:Facesitting:", f"<lora:{face}:")}
            for j in JOBS
        ]
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for need in ("Fern_id_v1", "Eyes_for_Illustrious_Lora_Perfect_anime_eyes"):
        if need not in names:
            raise RuntimeError(f"missing {need}; have={sorted(names)}")
    print("using face LoRA", face, flush=True)

    for job in jobs:
        txt2img(job)
    print("DONE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

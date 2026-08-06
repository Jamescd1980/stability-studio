"""Wild Fern keepers finish: facesit d65 probe, aftercare eyes-closed, upscale+AD."""
from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import requests
from PIL import Image

FORGE = "http://127.0.0.1:7860"
CKPT = "waijfu_alpha.safetensors"
SEED = 62847

I2I = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften\_bgcity_i2i"
)
KEEP = I2I / "_keepers"
OUT = I2I / "_finish"

FACESIT_SRC = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\Stills\forge_soften\facesit_darkness_pov_v3.png"
)
AFTERCARE_FORGE = Path(
    r"D:\ComfyBox Images and Videos\Images\Theater Jobs"
    r"\Where the Wild Fern Moans\review\fern_aftercare_forge_v1.png"
)

# User-picked denoise winners
KEEPERS = [
    ("01_kiss", I2I / "01_kiss_d40.png"),
    ("02_fern_licks", I2I / "02_fern_licks_d30.png"),
    ("04_fern_revcowgirl", I2I / "04_fern_revcowgirl_d50.png"),
    ("05_fern_doggy", I2I / "05_fern_doggy_d40.png"),
]

BG = (
    "loft bedroom at night in town, warm dark brown vertical wood panel walls, "
    "wood grain planks, cream conical lampshade with warm yellow glow, "
    "wooden window showing night city skyline with lit skyscrapers, no trees, "
    "white rumpled bed sheets, white pillows, "
    "dark wood bed headboard on the right of the frame, warm low key lamp light, "
)
QUALITY = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, "
    "anime++, bold outline, cel-shaded coloring, "
)
NEG = (
    "bad quality, worst quality, blurry, bad anatomy, "
    "purple walls, lavender walls, pine trees, trees outside window, forest, evergreen, "
    "cum, semen, white stains, fluids, fluid, camera, dslr, daytime, neon, "
    "man, male, penis, cock, 1boy"
)

AD_OFF = {"ADetailer": {"args": [False]}}


def ad_face(prompt: str, neg: str, strength: float = 0.35) -> dict:
    return {
        "ADetailer": {
            "args": [
                {
                    "ad_model": "face_yolov8n.pt",
                    "ad_prompt": prompt,
                    "ad_negative_prompt": neg,
                    "ad_confidence": 0.25,
                    "ad_dilate_erode": 4,
                    "ad_mask_blur": 4,
                    "ad_denoising_strength": strength,
                    "ad_inpaint_only_masked": True,
                    "ad_inpaint_padding": 32,
                }
            ]
        }
    }


def face_tag() -> str:
    requests.post(f"{FORGE}/sdapi/v1/refresh-loras", timeout=180)
    names = {x.get("name") for x in requests.get(f"{FORGE}/sdapi/v1/loras", timeout=60).json()}
    for n in ("Facesitting", "povFacesitting"):
        if n in names:
            return n
    return "Facesitting"


def to_b64(path: Path) -> str:
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        tmp = OUT / "_rgb" / f"{path.stem}.png"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(tmp, format="PNG")
    return base64.b64encode(tmp.read_bytes()).decode()


def img2img(
    *,
    src: Path,
    dest: Path,
    prompt: str,
    neg: str,
    denoise: float,
    w: int,
    h: int,
    ad: dict,
    seed: int = SEED,
    steps: int = 32,
    cfg: float = 6.0,
) -> Path:
    payload = {
        "init_images": [to_b64(src)],
        "prompt": prompt,
        "negative_prompt": neg,
        "denoising_strength": denoise,
        "steps": steps,
        "cfg_scale": cfg,
        "width": w,
        "height": h,
        "seed": seed,
        "sampler_name": "Euler a",
        "restore_faces": False,
        "resize_mode": 0,
        "override_settings": {"sd_model_checkpoint": CKPT},
        "override_settings_restore_afterwards": True,
        "alwayson_scripts": ad,
    }
    r = requests.post(f"{FORGE}/sdapi/v1/img2img", json=payload, timeout=2400)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["images"][0].split(",", 1)[-1])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return dest


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    KEEP.mkdir(parents=True, exist_ok=True)
    requests.post(
        f"{FORGE}/sdapi/v1/options",
        json={"sd_model_checkpoint": CKPT},
        timeout=600,
    )
    results = []

    # --- 1) Facesit probe at 0.65 ---
    face = face_tag()
    with Image.open(FACESIT_SRC) as im:
        fw, fh = im.size
    facesit_prompt = (
        f"<lora:{face}:0.55> <lora:Fern_id_v1:0.9> "
        + QUALITY
        + BG
        + "low angle looking up, facesitting, solo focus, 1girl, nb_fern, Fern, "
        "purple hair, purple eyes, completely nude, large breasts, pussy on face, "
        "looking down at viewer, blonde bangs, blue eyes looking up at bottom edge, "
        "wet pussy, cunnilingus"
    )
    facesit_neg = NEG + (
        ", blonde on top, blue eyes on Fern, purple eyes under, black hair under, "
        "two Ferns, closed eyes, eyes closed, clothes, lingerie"
    )
    dest_fs = OUT / "facesit_darkness_pov_v3_d65.png"
    print("=== facesit d65", flush=True)
    img2img(
        src=FACESIT_SRC,
        dest=dest_fs,
        prompt=facesit_prompt,
        neg=facesit_neg,
        denoise=0.65,
        w=fw,
        h=fh,
        ad=AD_OFF,
    )
    print("  OK", dest_fs, dest_fs.stat().st_size, flush=True)
    results.append({"step": "facesit_d65", "ok": True, "path": str(dest_fs)})

    # --- 2) Aftercare forged original → eyes closed (low body denoise, AD closed eyes) ---
    if not AFTERCARE_FORGE.is_file():
        raise FileNotFoundError(AFTERCARE_FORGE)
    with Image.open(AFTERCARE_FORGE) as im:
        aw, ah = im.size
    ac_prompt = (
        "<lora:Fern_id_v1:0.85> <lora:Darkness_id_v1:0.85> "
        + QUALITY
        + "loft bedroom at night, warm bedside lamp light, "
        "2girls, nb_fern, Fern, long purple hair, "
        "nbk_darkness, Darkness, long blonde hair, blonde ponytail, "
        "both completely nude, lying in bed together, aftercare, "
        "both eyes closed, sleeping, peaceful, soft, no sex act, yuri"
    )
    ac_neg = NEG + ", open eyes, looking at viewer, awake, staring"
    dest_ac = OUT / "06_aftercare_forge_eyes_closed.png"
    print("=== aftercare forge -> eyes closed", flush=True)
    img2img(
        src=AFTERCARE_FORGE,
        dest=dest_ac,
        prompt=ac_prompt,
        neg=ac_neg,
        denoise=0.18,
        w=aw,
        h=ah,
        ad={
            "ADetailer": {
                "args": [
                    {
                        "ad_model": "mediapipe_face_mesh_eyes_only",
                        "ad_prompt": (
                            "closed eyes, sleeping, soft eyelids, peaceful sleeping face"
                        ),
                        "ad_negative_prompt": (
                            "open eyes, looking at viewer, staring, wide eyes, awake, iris"
                        ),
                        "ad_confidence": 0.2,
                        "ad_dilate_erode": 2,
                        "ad_mask_blur": 4,
                        "ad_denoising_strength": 0.42,
                        "ad_inpaint_only_masked": True,
                        "ad_inpaint_padding": 24,
                    }
                ]
            }
        },
        steps=28,
        cfg=5.0,
    )
    print("  OK", dest_ac, dest_ac.stat().st_size, flush=True)
    results.append({"step": "aftercare_eyes", "ok": True, "path": str(dest_ac)})

    # --- 3) Promote keepers + Forge upscale (1536) with ADetailer ---
    for stem, src in KEEPERS:
        if not src.is_file():
            print("MISSING keeper", src, flush=True)
            results.append({"step": stem, "ok": False, "error": "missing"})
            continue
        kept = KEEP / f"{stem}.png"
        shutil.copy2(src, kept)
        with Image.open(kept) as im:
            w, h = im.size
        # square → 1536; non-square keep aspect toward ~1536 long edge
        if w == h:
            tw = th = 1536
        else:
            scale = 1536 / max(w, h)
            tw, th = int(w * scale), int(h * scale)
            # snap to multiples of 8
            tw, th = tw - tw % 8, th - th % 8

        prompt = (
            "<lora:Fern_id_v1:0.8> "
            + QUALITY
            + BG
            + "high quality skin, detailed, sharp details, clean linework"
        )
        dest = OUT / f"{stem}_up1536_ad.png"
        print(f"=== upscale+AD {stem} {w}x{h} -> {tw}x{th}", flush=True)
        img2img(
            src=kept,
            dest=dest,
            prompt=prompt,
            neg=NEG,
            denoise=0.28,
            w=tw,
            h=th,
            ad=ad_face(
                "anime face, soft diffuse catchlights, detailed iris, round pupils, "
                "clean eyes, soft lighting, natural skin",
                "lens flare, eye flare, sparkle eyes, glowing eyes, starburst, overexposed eyes",
                0.32,
            ),
            steps=28,
            cfg=5.5,
        )
        print("  OK", dest.name, Image.open(dest).size, dest.stat().st_size, flush=True)
        results.append({"step": f"{stem}_up", "ok": True, "path": str(dest)})

    (OUT / "_finish_summary.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    ok = sum(1 for x in results if x.get("ok"))
    print(f"DONE {ok}/{len(results)} -> {OUT}", flush=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

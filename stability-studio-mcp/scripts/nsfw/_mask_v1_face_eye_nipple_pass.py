"""mask_v1 casting-couch strip: face → eyes-only → nipple (breast AD) on Forge CUDA.

Inputs: Images/mask_v1_b*_forge_hardlock.png
Outputs: smoke/mask_v1/b*/ + Images/mask_v1_b*_{faceeyes,nipple}_hardlock.png
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import refine_image_forge  # noqa: E402

IMGS = Path(r"D:\ComfyBox Images and Videos\Images")
SMOKE = Path(
    r"D:\ComfyBox Images and Videos\assets\blender\sets\casting_couch\smoke\mask_v1"
)
PLATE = Path(
    r"D:\ComfyBox Images and Videos\assets\blender\sets\casting_couch\plates\camWide_empty_B.png"
)

CKPT = "waijfu_alpha.safetensors"

FACE_AD = (
    "nbk_darkness, Darkness, detailed face, beautiful detailed blue eyes, "
    "sharp iris, clear catchlights, detailed eyelashes, heavy blush, "
    "nervous embarrassed expression, perfect anime face, clean lineart"
)
FACE_NEG = (
    "blurry face, deformed face, brown eyes, hazel eyes, glowing eyes, "
    "star pupils, blank eyes, extra eyes, watermark"
)
EYES_AD = (
    "beautiful detailed blue eyes, sharp round iris, clear catchlights, "
    "detailed eyelashes, anime eyes, nbk_darkness"
)
EYES_NEG = "brown eyes, hazel eyes, glowing eyes, star pupils, blank eyes, deformed eyes"
NIPPLE_AD = (
    "detailed nipples, textured areola, natural pink nipples, "
    "sharp focus, clean lineart, anime nipples"
)
NIPPLE_NEG = (
    "censored, mosaic, bar censor, deformed nipples, extra nipples, "
    "blurry, lowres, watermark"
)

BEATS = {
    "b1": {
        "prompt": (
            "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
            "full body, feet visible, standing on the rug, looking at viewer, solo, 1girl, "
            "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
            "red x hair ornament, large breasts, nervous expression, heavy blush, "
            "worried look, hands clasped in front of her waist, necktie, bare shoulders, "
            "collared holter neck, white crop top, micro shorts, midriff, navel, "
            "blue denim micro shorts, barefoot, perfect eyes, soft contact shadow on rug"
        ),
        "neg": (
            "extra people, 1boy, man, male, male hand, close-up, portrait, cropped legs, "
            "camera, dslr, cum, semen, transparent legs, see-through, lowres, bad anatomy, "
            "bad hands, blurry"
        ),
        "seed": 7501,
        "do_nipple": False,  # clothed — face/eyes only
    },
    "b2": {
        "prompt": (
            "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
            "full body, feet visible, standing on the rug, looking at viewer, solo, 1girl, "
            "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
            "red x hair ornament, large breasts, embarrassed expression, heavy blush, "
            "shy look, hands behind back, arms behind back, wearing skimpy white sports bra, "
            "black straps, no shirt, micro shorts, midriff, navel, blue denim micro shorts, "
            "barefoot, perfect eyes, soft contact shadow on rug"
        ),
        "neg": (
            "shirt, blouse, holter, necktie, hands in front, holding breasts, topless, "
            "nipples, extra people, 1boy, man, male, male hand, close-up, portrait, "
            "cropped legs, camera, dslr, cum, semen, transparent legs, see-through, "
            "lowres, bad anatomy, bad hands, blurry"
        ),
        "seed": 7502,
        "do_nipple": False,  # sports bra — face/eyes only
    },
    "b3": {
        "prompt": (
            "masterpiece, best quality, anime++, bold outline, cel-shaded coloring, "
            "full body, feet visible, standing on the rug, looking at viewer, solo, 1girl, "
            "nbk_darkness, Darkness, long blonde hair, blonde ponytail, blue eyes, "
            "red x hair ornament, large breasts, embarrassed expression, heavy blush, "
            "shy look, topless, nude breasts, breast hold, hands under breasts lifting them up, "
            "erect nipples, detailed nipples, textured areola, micro shorts, midriff, navel, "
            "blue denim micro shorts, barefoot, perfect eyes, soft contact shadow on rug"
        ),
        "neg": (
            "bra, shirt, blouse, covered breasts, hands behind back, extra people, 1boy, "
            "man, male, male hand, close-up, portrait, cropped legs, camera, dslr, cum, "
            "semen, transparent legs, see-through, lowres, bad anatomy, bad hands, blurry, "
            "censored, mosaic"
        ),
        "seed": 7503,
        "do_nipple": True,
    },
}


def hardlock(src: Path, mask: Path, dest: Path, review: Path) -> dict:
    plate_im = Image.open(PLATE).convert("RGBA")
    forge_im = Image.open(src).convert("RGBA")
    if forge_im.size != plate_im.size:
        forge_im = forge_im.resize(plate_im.size, Image.Resampling.LANCZOS)
    mask_im = Image.open(mask).convert("L").filter(ImageFilter.GaussianBlur(radius=1.2))
    if mask_im.size != plate_im.size:
        mask_im = mask_im.resize(plate_im.size, Image.Resampling.BILINEAR)
    out = Image.composite(forge_im, plate_im, mask_im).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    shutil.copy2(dest, review)
    m = np.asarray(
        Image.open(mask).convert("L").resize(plate_im.size, Image.Resampling.NEAREST)
    )
    bg = np.asarray(plate_im.convert("RGB"), dtype=np.int16)
    res = np.asarray(out, dtype=np.int16)
    outside = m < 8
    diff = np.abs(res - bg).mean(axis=2)
    return {
        "outside_mean": float(diff[outside].mean()),
        "exact0_pct": round(float((diff[outside] == 0).mean()) * 100, 2),
    }


def refine(cfg, label: str, image: Path, **kw) -> Path:
    print(f"\n=== {label} ===", flush=True)
    r = refine_image_forge(cfg, image_path=str(image), checkpoint=CKPT, **kw)
    print(
        json.dumps({k: r.get(k) for k in ("ok", "error", "saved_files")}, default=str)[
            :500
        ],
        flush=True,
    )
    if not r.get("ok"):
        raise SystemExit(f"fail {label}: {r}")
    return Path(r["saved_files"][0])


def main() -> int:
    cfg = load_config()
    results = {}
    for bid, spec in BEATS.items():
        src = IMGS / f"mask_v1_{bid}_forge_hardlock.png"
        if not src.is_file():
            raise SystemExit(f"missing {src}")
        mask = SMOKE / bid / "mask_dilate.png"
        work = SMOKE / bid

        face = refine(
            cfg,
            f"{bid}_face",
            src,
            prompt=spec["prompt"],
            negative_prompt=spec["neg"],
            denoising_strength=0.06,
            steps=24,
            cfg_scale=5.0,
            seed=spec["seed"],
            adetailer=True,
            ad_prompt=FACE_AD,
            ad_negative=FACE_NEG,
            ad_model="face_yolov8n.pt",
            ad_denoising_strength=0.35,
        )
        eyes = refine(
            cfg,
            f"{bid}_eyes",
            face,
            prompt=spec["prompt"],
            negative_prompt=spec["neg"],
            denoising_strength=0.05,
            steps=20,
            cfg_scale=5.0,
            seed=spec["seed"] + 10,
            adetailer=True,
            ad_prompt=EYES_AD,
            ad_negative=EYES_NEG,
            ad_model="mediapipe_face_mesh_eyes_only",
            ad_denoising_strength=0.28,
        )
        eyes_dest = work / f"{bid}_faceeyes.png"
        shutil.copy2(eyes, eyes_dest)
        stats_fe = hardlock(
            eyes_dest,
            mask,
            work / f"{bid}_faceeyes_hardlock.png",
            IMGS / f"mask_v1_{bid}_faceeyes_hardlock.png",
        )
        shutil.copy2(eyes_dest, IMGS / f"mask_v1_{bid}_faceeyes.png")

        nipple_path = None
        stats_n = None
        if spec.get("do_nipple"):
            # Drop anti-nipple tags from beat negs so breast AD can work.
            nip_neg = ", ".join(
                t.strip()
                for t in spec["neg"].split(",")
                if t.strip() and t.strip() not in {"nipples", "topless"}
            )
            nip_neg = f"{nip_neg}, {NIPPLE_NEG}"
            nipple = refine(
                cfg,
                f"{bid}_nipple",
                eyes,
                prompt=spec["prompt"]
                + ", detailed nipples, textured areola",
                negative_prompt=nip_neg,
                denoising_strength=0.05,
                steps=20,
                cfg_scale=5.0,
                seed=spec["seed"] + 20,
                adetailer=True,
                ad_prompt=NIPPLE_AD,
                ad_negative=NIPPLE_NEG,
                ad_model="female-breast-v4.7.pt",
                ad_denoising_strength=0.32,
            )
            nipple_dest = work / f"{bid}_nipple.png"
            shutil.copy2(nipple, nipple_dest)
            stats_n = hardlock(
                nipple_dest,
                mask,
                work / f"{bid}_nipple_hardlock.png",
                IMGS / f"mask_v1_{bid}_nipple_hardlock.png",
            )
            shutil.copy2(nipple_dest, IMGS / f"mask_v1_{bid}_nipple.png")
            nipple_path = str(IMGS / f"mask_v1_{bid}_nipple_hardlock.png")

        results[bid] = {
            "faceeyes": str(IMGS / f"mask_v1_{bid}_faceeyes_hardlock.png"),
            "faceeyes_lock": stats_fe,
            "nipple": nipple_path,
            "nipple_lock": stats_n,
        }
        print(bid, results[bid], flush=True)

    print("DONE", json.dumps(results, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

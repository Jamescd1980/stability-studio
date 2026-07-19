"""Pass3: BJ eyes-only + doggy face-only from ORIGINAL imports (crisp, no soft pass2)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.forge_backend import forge_is_reachable, refine_image_forge, switch_stills_backend  # noqa: E402

from frieren_sex_scenes_refine_kit import (  # noqa: E402
    CHECKPOINT,
    IMPORT_DIR,
    OUT_DIR,
    SCENE_PACKS,
    SCENE_PACKS_DIR,
)

PASS3 = IMPORT_DIR / "_refined" / "pass3"

CHAR = (
    "nb_frieren, frieren, elf girl, long silver white hair, twin tails, "
    "pointed ears, red teardrop earrings, pale skin, nude, completely nude, "
    "masterpiece, best quality, highly detailed, sharp focus, crisp lines, "
    "anime illustration, <lora:Frieren:0.8>"
)

EYES_AD = (
    "nb_frieren, beautiful detailed eyes, sharp iris, clear catchlights, "
    "detailed eyelashes, green eyes, high detail eyes, "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.9>"
)

FACE_AD = (
    "nb_frieren, detailed face, beautiful detailed eyes, sharp iris, "
    "clear catchlights, sharp lips, detailed eyelashes, green eyes, "
    "crisp anime face, <lora:Frieren:0.7>, "
    "<lora:Eyes_for_Illustrious_Lora_Perfect_anime_eyes:0.85>"
)

NEG = (
    "lowres, blurry, soft focus, oversmoothed, plastic skin, bad anatomy, "
    "shirt, collar, blouse, clothing, watermark, text, worst quality, "
    "empty mouth, removed penis, small penis"
)

BJ_JOBS = [
    {
        "name": "Frierenbj4.png",
        "prompt": (
            CHAR
            + ", blowjob, fellatio, deepthroat, thick cock in mouth, "
            "lips wrapped around cock, side view, kneeling, bedroom night"
        ),
    },
    {
        "name": "Frierenbj6.png",
        "prompt": (
            CHAR
            + ", blowjob, fellatio, thick cock in mouth, lips sealed around cock, "
            "pov looking up, bedroom night"
        ),
    },
    {
        "name": "Frierenbj7.png",
        "prompt": (
            CHAR
            + ", blowjob, fellatio, deepthroat, thick cock in mouth, "
            "lips wrapped around cock, pov looking up, hands holding twin tails, "
            "bedroom night"
        ),
    },
]

DOGGY = {
    "name": "Frieren_Doggystyle3.png",
    "prompt": (
        CHAR
        + ", doggystyle, sex, penetration, cock in pussy, pussy, "
        "looking back over shoulder, bare shoulders, black choker only, "
        "hands gripping ass, thumbs pressing into buttocks, finger dig, "
        "pov, bedroom night, sharp details"
    ),
}


def run_one(cfg: dict, *, src: Path, dest: Path, prompt: str, mode: str) -> dict:
    if mode == "eyes":
        kwargs = dict(
            adetailer=True,
            ad_model="mediapipe_face_mesh_eyes_only",
            ad_prompt=EYES_AD,
            ad_negative="blurry eyes, dull eyes, deformed eyes, soft eyes",
            ad_denoising_strength=0.38,
            ad_dilate_erode=2,
            ad_mask_padding=16,
            denoising_strength=0.06,  # near-lock body/mouth/cock
        )
    else:  # face
        kwargs = dict(
            adetailer=True,
            ad_model="face_yolov8n.pt",
            ad_prompt=FACE_AD,
            ad_negative="blurry face, soft face, shirt collar, clothing",
            ad_denoising_strength=0.36,
            ad_dilate_erode=3,
            ad_mask_padding=24,
            denoising_strength=0.08,  # keep thumb grip / body crisp
        )

    print(f"REFINE[{mode}] {src.name} → {dest.name}", flush=True)
    result = refine_image_forge(
        cfg,
        image_path=str(src),
        prompt=prompt,
        negative_prompt=NEG,
        checkpoint=CHECKPOINT,
        steps=28,
        cfg_scale=5.5,
        seed=-1,
        **kwargs,
    )
    if not result.get("ok"):
        return {"ok": False, "src": str(src), "mode": mode, "result": result}
    saved = result.get("saved_files") or []
    if not saved:
        return {"ok": False, "src": str(src), "error": "no saved"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(saved[0], dest)
    return {
        "ok": True,
        "src": str(src),
        "output": str(dest),
        "mode": mode,
        "ad_model": kwargs["ad_model"],
        "body_denoise": kwargs["denoising_strength"],
        "ad_denoise": kwargs["ad_denoising_strength"],
    }


def promote_and_pack(results: list[dict]) -> dict:
    promoted = []
    for r in results:
        if not r.get("ok"):
            continue
        out = Path(r["output"])
        # Frierenbj7_pass3.png -> Frierenbj7_forge.png
        master = OUT_DIR / out.name.replace("_pass3.png", "_forge.png")
        shutil.copy2(out, master)
        promoted.append(str(master))

    copied = []
    for pack, names in SCENE_PACKS.items():
        pack_dir = SCENE_PACKS_DIR / pack
        pack_dir.mkdir(parents=True, exist_ok=True)
        for i, src_name in enumerate(names, start=1):
            src = OUT_DIR / f"{Path(src_name).stem}_forge.png"
            if not src.is_file():
                continue
            dest = pack_dir / f"{i:02d}_{src.name}"
            shutil.copy2(src, dest)
            copied.append(str(dest))
    return {"promoted": promoted, "packs": copied}


def main() -> int:
    cfg = load_config()
    PASS3.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not forge_is_reachable(cfg):
        print("SWITCH forge…", flush=True)
        sw = switch_stills_backend(cfg, backend="forge", wait=True)
        print(json.dumps({k: sw.get(k) for k in ("ok", "error")}, indent=2), flush=True)
    if not forge_is_reachable(cfg):
        print("Forge not reachable", flush=True)
        return 1

    results: list[dict] = []
    for job in BJ_JOBS:
        src = IMPORT_DIR / job["name"]
        dest = PASS3 / f"{Path(job['name']).stem}_pass3.png"
        results.append(run_one(cfg, src=src, dest=dest, prompt=job["prompt"], mode="eyes"))
        print(json.dumps({k: results[-1].get(k) for k in ("ok", "output", "error")}, indent=2), flush=True)

    dog_src = IMPORT_DIR / DOGGY["name"]
    dog_dest = PASS3 / "Frieren_Doggystyle3_pass3.png"
    results.append(
        run_one(cfg, src=dog_src, dest=dog_dest, prompt=DOGGY["prompt"], mode="face")
    )
    print(json.dumps({k: results[-1].get(k) for k in ("ok", "output", "error")}, indent=2), flush=True)

    pack = promote_and_pack(results)
    summary = {"ok": all(r.get("ok") for r in results), "results": results, "pack": pack}
    out_json = ROOT / "outputs" / "frieren_sex_scenes_pass3_eyes_face.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

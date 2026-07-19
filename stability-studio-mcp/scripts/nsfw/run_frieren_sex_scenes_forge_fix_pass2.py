"""Pass2 fix: oral insertion lock (no ADetailer) + doggy collar remove.

Uses explicit NSFW tags. Sources are original imports (not broken pass1).
"""

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

PASS2 = IMPORT_DIR / "_refined" / "pass2"

BASE_CHAR = (
    "nb_frieren, frieren, elf girl, long silver white hair, twin tails, "
    "pointed ears, red teardrop earrings, pale skin, nude, completely nude, "
    "masterpiece, best quality, highly detailed, anime illustration, "
    "<lora:Frieren:0.8>"
)

NEG_COMMON = (
    "lowres, bad anatomy, bad hands, extra fingers, missing fingers, "
    "mutated hands, deformed face, blurry, worst quality, jpeg artifacts, "
    "watermark, text, logo, shirt, blouse, clothing, clothes, "
    "star pupils, glowing eyes"
)

NEG_ORAL = (
    NEG_COMMON
    + ", empty mouth, open mouth without cock, penis outside mouth, "
    "removed penis, missing penis, small penis, tiny cock, shrinking penis, "
    "limp penis, soft penis, floating penis, penis away from face, "
    "closed mouth, no oral, no blowjob"
)

ORAL_JOBS = [
    {
        "name": "Frierenbj4.png",
        "prompt": (
            BASE_CHAR
            + ", blowjob, fellatio, deepthroat, cock in mouth, "
            "lips wrapped around cock, penis in mouth, oral sex, "
            "kneeling, side view, bedroom night, detailed eyes, "
            "keep cock thick and inserted in mouth"
        ),
        "denoise": 0.20,
    },
    {
        "name": "Frierenbj6.png",
        "prompt": (
            BASE_CHAR
            + ", blowjob, fellatio, cock in mouth, lips sealed around cock, "
            "penis in mouth, oral sex, pov, looking up, bedroom night, "
            "detailed eyes, thick erect cock in mouth, no gap"
        ),
        "denoise": 0.20,
    },
    {
        "name": "Frierenbj7.png",
        "prompt": (
            BASE_CHAR
            + ", blowjob, fellatio, cock in mouth, deepthroat, "
            "lips wrapped around thick cock, penis fully in mouth, "
            "oral sex, pov looking up, hands holding twin tails, "
            "bedroom night, detailed eyes, keep insertion"
        ),
        "denoise": 0.20,
    },
]

DOGGY = {
    "name": "Frieren_Doggystyle3.png",
    # Prefer pass1 (great quality) as base so we only strip collar, not rebuild scene.
    "source": OUT_DIR / "Frieren_Doggystyle3_forge.png",
    "fallback": IMPORT_DIR / "Frieren_Doggystyle3.png",
    "prompt": (
        BASE_CHAR
        + ", doggystyle, sex, penetration, pussy, cock in pussy, "
        "looking back over shoulder, completely nude, bare shoulders, "
        "bare back, black choker only, no shirt, no collar, no clothing, "
        "pov, bedroom night, detailed eyes"
    ),
    "negative": (
        NEG_COMMON
        + ", shirt, collar, blouse, neckline, white collar, clothing on neck, "
        "fabric on shoulders, dressed, clothed"
    ),
    "denoise": 0.22,
}


def refine(
    cfg: dict,
    *,
    src: Path,
    dest: Path,
    prompt: str,
    negative: str,
    denoise: float,
    adetailer: bool,
) -> dict:
    print(f"REFINE {src.name} denoise={denoise} ad={adetailer} → {dest.name}", flush=True)
    result = refine_image_forge(
        cfg,
        image_path=str(src),
        prompt=prompt,
        negative_prompt=negative,
        checkpoint=CHECKPOINT,
        denoising_strength=denoise,
        steps=28,
        cfg_scale=5.5,
        seed=-1,
        adetailer=adetailer,
        ad_prompt="",
    )
    if not result.get("ok"):
        return {"ok": False, "src": str(src), "result": result}
    saved = result.get("saved_files") or []
    if not saved:
        return {"ok": False, "src": str(src), "error": "no saved_files"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(saved[0], dest)
    return {
        "ok": True,
        "src": str(src),
        "output": str(dest),
        "denoise": denoise,
        "adetailer": adetailer,
    }


def promote_and_pack(results: list[dict]) -> dict:
    promoted = []
    for r in results:
        if not r.get("ok"):
            continue
        out = Path(r["output"])
        # Map pass2 names back to pass1 master names
        name = out.name.replace("_pass2.png", "_forge.png")
        # oral: Frierenbj4_pass2.png -> Frierenbj4_forge.png
        dest = OUT_DIR / name
        backup = OUT_DIR / name.replace("_forge.png", "_forge_pass1_bad.png")
        if dest.is_file() and not backup.is_file():
            # only backup once if prior was the bad oral/collar version
            shutil.copy2(dest, backup)
        shutil.copy2(out, dest)
        promoted.append({"from": str(out), "to": str(dest), "backup": str(backup)})

    # refresh packs
    SCENE_PACKS_DIR.mkdir(parents=True, exist_ok=True)
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
    return {"promoted": promoted, "pack_files": copied}


def main() -> int:
    cfg = load_config()
    PASS2.mkdir(parents=True, exist_ok=True)

    print("SWITCH forge…", flush=True)
    sw = switch_stills_backend(cfg, backend="forge", wait=True)
    print(json.dumps({k: sw.get(k) for k in ("ok", "error", "comfyui_running")}, indent=2), flush=True)
    if not forge_is_reachable(cfg):
        # SSH may time out while forge is already up
        if not (sw.get("forge") or {}).get("running"):
            print("Forge not reachable", flush=True)
            print(json.dumps(sw, indent=2)[:3000], flush=True)
            return 1

    results: list[dict] = []

    for job in ORAL_JOBS:
        src = IMPORT_DIR / job["name"]
        dest = PASS2 / f"{Path(job['name']).stem}_pass2.png"
        r = refine(
            cfg,
            src=src,
            dest=dest,
            prompt=job["prompt"],
            negative=NEG_ORAL,
            denoise=float(job["denoise"]),
            adetailer=False,
        )
        results.append(r)
        print(json.dumps({k: r.get(k) for k in ("ok", "output", "error")}, indent=2), flush=True)

    dog_src = DOGGY["source"] if DOGGY["source"].is_file() else DOGGY["fallback"]
    dog_dest = PASS2 / "Frieren_Doggystyle3_pass2.png"
    r = refine(
        cfg,
        src=dog_src,
        dest=dog_dest,
        prompt=DOGGY["prompt"],
        negative=DOGGY["negative"],
        denoise=float(DOGGY["denoise"]),
        adetailer=False,
    )
    results.append(r)
    print(json.dumps({k: r.get(k) for k in ("ok", "output", "error")}, indent=2), flush=True)

    pack = promote_and_pack(results)
    summary = {"ok": all(x.get("ok") for x in results), "results": results, "pack": pack}
    out_json = ROOT / "outputs" / "frieren_sex_scenes_forge_fix_pass2.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

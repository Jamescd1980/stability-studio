"""Escalate failed Forge stills via Comfy ControlNet + Eyes LoRA, then light Forge polish."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog  # noqa: E402
from studio.config import catalog_path, load_config  # noqa: E402
from studio.engine import GenerationEngine  # noqa: E402
from studio.forge_backend import refine_image_forge, switch_stills_backend  # noqa: E402

from frieren_sex_scenes_refine_kit import (  # noqa: E402
    AD_PROMPT,
    CHECKPOINT,
    GLOBAL_PROMPT,
    IMPORT_DIR,
    NEGATIVE,
)

ESCALATE_DIR = IMPORT_DIR / "_refined" / "escalate"
PASS1 = IMPORT_DIR / "_refined" / "pass1"

# Original imports as pose guides (not forge outputs).
JOBS = [
    {
        "id": "Stage3",
        "guide": "Frieren_Stage3.png",
        "prompt": (
            "nb_frieren, frieren, nude elf girl on all fours looking back, "
            "holding purple dildo against buttocks, sex toy on rug, bedroom, "
            "purple bedding, daylight window, detailed hands holding toy, "
            "masterpiece, best quality, highly detailed face and eyes, "
            "sharp lips, clean anatomy"
        ),
        "depth": 0.55,
        "canny": 0.65,
    },
    {
        "id": "bj7",
        "guide": "Frierenbj7.png",
        "prompt": (
            "nb_frieren, frieren, nude elf girl kneeling on bed, fellatio POV, "
            "looking up, partner hands holding twin tails, detailed fingers, "
            "bedroom night window, masterpiece, best quality, "
            "highly detailed face and eyes, sharp lips, clean hand anatomy"
        ),
        "depth": 0.55,
        "canny": 0.68,
    },
]


def build_loras(catalog: dict) -> list[dict]:
    frieren = (catalog.get("character_loras") or {}).get("frieren") or {}
    eyes = None
    for pair in frieren.get("pair_with") or []:
        eyes = pair
        break
    out = []
    if frieren.get("file"):
        out.append(
            {
                "file": frieren["file"],
                "weight": float(frieren.get("weight") or 0.8),
            }
        )
    if eyes and eyes.get("file"):
        out.append(
            {
                "file": eyes["file"],
                "weight": float(eyes.get("weight") or 0.8),
            }
        )
    return out


def main() -> int:
    cfg = load_config()
    ESCALATE_DIR.mkdir(parents=True, exist_ok=True)

    print("SWITCH comfy…", flush=True)
    sw = switch_stills_backend(cfg, backend="comfy", wait=True)
    print(json.dumps(sw, indent=2)[:2500], flush=True)

    catalog_obj = StyleCatalog(catalog_path(cfg), cfg)
    engine = GenerationEngine(cfg, catalog_obj)
    catalog = catalog_obj._data  # noqa: SLF001
    loras = build_loras(catalog)
    print("loras", loras, flush=True)

    comfy_outs: list[dict] = []
    for job in JOBS:
        guide = IMPORT_DIR / job["guide"]
        if not guide.is_file():
            comfy_outs.append({"id": job["id"], "ok": False, "error": f"missing {guide}"})
            continue
        print(f"\n===== ESCALATE Comfy {job['id']} =====", flush=True)
        try:
            result = engine.generate_image_controlnet(
                guide_image_path=str(guide),
                prompt=job["prompt"],
                style="waijfu",
                negative_prompt=NEGATIVE + ", bad hands, fused fingers, extra fingers",
                loras=loras,
                width=1024,
                height=1024,
                cfg=5.5,
                steps=30,
                depth_strength=float(job["depth"]),
                canny_strength=float(job["canny"]),
                face_detail=False,
                backend="comfyui",
                content_rating="open",
            )
        except Exception as exc:
            print(f"FAIL {job['id']}: {exc}", flush=True)
            comfy_outs.append({"id": job["id"], "ok": False, "error": str(exc)})
            continue

        saved = result.get("saved_files") or []
        copied = []
        for p in saved:
            src = Path(str(p))
            if not src.is_file():
                continue
            dest = ESCALATE_DIR / f"{job['id']}_comfy_{src.name}"
            shutil.copy2(src, dest)
            copied.append(str(dest))
        comfy_outs.append({"id": job["id"], "ok": True, "copied": copied, "guide": str(guide)})
        print("OK", copied, flush=True)

    # Light Forge polish on successful Comfy outs
    ok_paths = [Path(p) for r in comfy_outs if r.get("ok") for p in (r.get("copied") or [])]
    if not ok_paths:
        summary = {"ok": False, "comfy": comfy_outs}
        (ROOT / "outputs" / "frieren_sex_scenes_escalate.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return 2

    print("\nSWITCH forge for light polish…", flush=True)
    sw2 = switch_stills_backend(cfg, backend="forge", wait=True)
    print(json.dumps({k: sw2.get(k) for k in ("ok", "error")}, indent=2), flush=True)
    # Proceed if forge reachable even if SSH timed out
    from studio.forge_backend import forge_is_reachable

    if not forge_is_reachable(cfg):
        print("Forge not reachable after switch", flush=True)
        return 3

    polish_outs = []
    for src in ok_paths:
        dest = ESCALATE_DIR / f"{src.stem}_forge.png"
        # Also write into pass1 as replacement masters
        pass1_name = {
            "Stage3": "Frieren_Stage3_forge.png",
            "bj7": "Frierenbj7_forge.png",
        }
        stem_key = "Stage3" if "Stage3" in src.name else ("bj7" if "bj7" in src.name else None)
        print(f"POLISH {src.name}", flush=True)
        result = refine_image_forge(
            cfg,
            image_path=str(src),
            prompt=GLOBAL_PROMPT,
            negative_prompt=NEGATIVE,
            checkpoint=CHECKPOINT,
            denoising_strength=0.22,
            steps=24,
            cfg_scale=5.0,
            seed=-1,
            adetailer=True,
            ad_prompt=AD_PROMPT,
        )
        if not result.get("ok"):
            polish_outs.append({"ok": False, "src": str(src), "result": result})
            continue
        saved = result.get("saved_files") or []
        if not saved:
            polish_outs.append({"ok": False, "src": str(src), "error": "no saved"})
            continue
        shutil.copy2(saved[0], dest)
        entry = {"ok": True, "src": str(src), "polished": str(dest)}
        if stem_key and stem_key in pass1_name:
            # Keep prior forge as backup, promote escalate polish to pass1
            backup = PASS1 / (pass1_name[stem_key].replace("_forge.png", "_forge_pre_escalate.png"))
            current = PASS1 / pass1_name[stem_key]
            if current.is_file() and not backup.is_file():
                shutil.copy2(current, backup)
            shutil.copy2(dest, current)
            entry["promoted_pass1"] = str(current)
            entry["backup"] = str(backup)
        polish_outs.append(entry)
        print("OK", entry, flush=True)

    summary = {"ok": all(p.get("ok") for p in polish_outs), "comfy": comfy_outs, "polish": polish_outs}
    out_json = ROOT / "outputs" / "frieren_sex_scenes_escalate.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("DONE", out_json, flush=True)
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

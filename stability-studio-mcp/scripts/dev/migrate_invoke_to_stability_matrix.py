"""Move worth-keeping Invoke standalone assets into Stability Matrix model folders."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
from _bootstrap import ROOT  # noqa: E402

from studio.config import load_config  # noqa: E402

SKIP_FLAT = {
    "animagine-xl-4.0.safetensors": "duplicate of -opt",
    "AnimeAnything_SD15.safetensors": "non-standard small bundle",
    "undressing_xl_v1.safetensors": "niche LoRA — not migrated",
    "hinaTuningFaceDetailer_SDXL-v2-rank256-pruned.safetensors": "already in SM Lora",
}


def _flat_moves(invoke_flat: Path) -> list[tuple[Path, str, str]]:
    return [
        (invoke_flat / "animagine-xl-4.0-opt.safetensors", "StableDiffusion", "SDXL anime checkpoint"),
        (invoke_flat / "CelshadedArtStylev2.safetensors", "Lora", "cel-shaded style LoRA"),
        (invoke_flat / "jyunzaburou.safetensors", "Lora", "style LoRA"),
        (invoke_flat / "Manga_Art_Style_NSFW_E43.safetensors", "Lora", "manga style LoRA"),
        (invoke_flat / "NSFWFilterXL_animagine.safetensors", "Lora", "pairs with Animagine XL"),
        (invoke_flat / "OpenPoseXL2.safetensors", "ControlNet", "SDXL OpenPose ControlNet"),
    ]


def _store_moves(invoke_store: Path) -> list[tuple[Path, str, str]]:
    return [
        (
            invoke_store / "2c722205-9ad8-413f-83c9-29b3456debe2" / "ip-adapter_sd15.safetensors",
            "IpAdapters15",
            "SD1.5 IP-Adapter base",
        ),
        (
            invoke_store / "6aa47332-3e7e-46f5-b834-9fa7c9b77ea2" / "ip-adapter-plus_sd15.safetensors",
            "IpAdapters15",
            "SD1.5 IP-Adapter Plus",
        ),
        (
            invoke_store / "916d1ab8-664e-4637-bb12-7b6cc50fbe39" / "ip-adapter-plus-face_sd15.safetensors",
            "IpAdapters15",
            "SD1.5 IP-Adapter Plus Face",
        ),
        (
            invoke_store / "70ad55d3-0f87-4820-8820-17385502972a" / "ip-adapter_sdxl_vit-h.safetensors",
            "IpAdaptersXl",
            "SDXL IP-Adapter ViT-H",
        ),
        (
            invoke_store / "93ae4f99-cbe3-4615-9459-bdbca6f86d5e" / "2x-AnimeSharpV4_RCAN.safetensors",
            "RealESRGAN",
            "2x anime upscale",
        ),
    ]


def _move(src: Path, dest_dir: Path, note: str) -> dict:
    entry: dict = {"source": str(src), "dest_dir": str(dest_dir), "note": note}
    if not src.is_file():
        entry["status"] = "missing"
        return entry
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.is_file():
        if dest.stat().st_size == src.stat().st_size:
            entry["status"] = "already_present"
            entry["dest"] = str(dest)
            return entry
        entry["status"] = "dest_exists_different_size"
        entry["dest"] = str(dest)
        return entry
    shutil.move(str(src), str(dest))
    entry["status"] = "moved"
    entry["dest"] = str(dest)
    entry["size_bytes"] = dest.stat().st_size
    return entry


def main() -> None:
    cfg = load_config()
    sm_models = Path(cfg["stability_matrix"]["models"])

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sm-models",
        type=Path,
        default=sm_models,
        help="Stability Matrix Data/Models (default: config.yaml)",
    )
    parser.add_argument(
        "--invoke-flat",
        type=Path,
        required=True,
        help="Folder of flat Invoke checkpoint/LoRA files",
    )
    parser.add_argument(
        "--invoke-store",
        type=Path,
        required=True,
        help="Invoke UUID model store root",
    )
    args = parser.parse_args()

    log: dict = {
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "sm_models": str(args.sm_models),
        "moves": [],
        "skipped_flat": SKIP_FLAT,
        "not_migrated": [
            "Invoke Flux / Z-Image / diffusers UUID trees (Comfy uses different loaders; miracle_nsfw covers Flux2)",
            "Duplicate OpenPoseXL2 in Arts UUID store",
            "animagine-xl-4.0 non-opt duplicate",
        ],
    }

    for src, subdir, note in _flat_moves(args.invoke_flat) + _store_moves(args.invoke_store):
        log["moves"].append(_move(src, args.sm_models / subdir, note))

    out = ROOT / "outputs" / "invoke_migration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(json.dumps(log, indent=2))
    moved = sum(1 for m in log["moves"] if m.get("status") == "moved")
    print(f"\nMoved {moved} files. Log: {out}")


if __name__ == "__main__":
    main()

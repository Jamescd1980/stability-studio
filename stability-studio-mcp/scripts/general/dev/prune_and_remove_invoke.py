"""Delete pruned checkpoints and standalone Invoke AI install."""
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

PRUNED_CHECKPOINTS = [
    "divineelegancemix_V10 (1).safetensors",
    "cyberrealisticPony_v170.safetensors",
    "cyberrealisticPony_v160.safetensors",
    "cyberrealistic_final.safetensors",
    "sdxlNSFW_v50.safetensors",
]

REMOVED_STYLES = [
    "cyberpunk",
    "sdxl_general",
    "divine_elegance",
    "photorealistic",
    "photorealistic_pony",
    "photorealistic_pony_v160",
    "sdxl_nsfw",
]


def main() -> None:
    cfg = load_config()
    sm_ckpt = Path(cfg["stability_matrix"]["models"]) / "StableDiffusion"
    invoke_pkg = Path(cfg["stability_matrix"]["packages"]["comfyui"]).parents[1] / "InvokeAI"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sm-checkpoints", type=Path, default=sm_ckpt)
    parser.add_argument(
        "--invoke-path",
        type=Path,
        action="append",
        default=[],
        help="Extra Invoke-related folders to delete (repeatable)",
    )
    parser.add_argument("--invoke-package", type=Path, default=invoke_pkg)
    args = parser.parse_args()

    invoke_paths = [args.invoke_package, *args.invoke_path]

    log: dict = {
        "pruned_at": datetime.now(timezone.utc).isoformat(),
        "removed_styles": REMOVED_STYLES,
        "checkpoints": [],
        "invoke_paths": [],
    }

    for name in PRUNED_CHECKPOINTS:
        path = args.sm_checkpoints / name
        entry = {"file": name, "path": str(path)}
        if path.is_file():
            entry["size_bytes"] = path.stat().st_size
            path.unlink()
            entry["status"] = "deleted"
        else:
            entry["status"] = "missing"
        log["checkpoints"].append(entry)

    for root in invoke_paths:
        entry = {"path": str(root)}
        if root.exists():
            entry["status"] = "deleted"
            shutil.rmtree(root)
        else:
            entry["status"] = "missing"
        log["invoke_paths"].append(entry)

    out = ROOT / "outputs" / "invoke_prune.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(json.dumps(log, indent=2))
    print(f"\nLog: {out}")


if __name__ == "__main__":
    main()

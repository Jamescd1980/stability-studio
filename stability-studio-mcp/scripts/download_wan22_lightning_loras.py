"""Download Wan 2.2 I2V LightX2V distill HIGH/LOW → local SM Lora/ + scp to ComfyBox."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.wan_assets import download_asset, model_dirs  # noqa: E402

ENTRIES = [
    {
        "filename": "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors",
        "folder": "loras",
        "repo": "lightx2v/Wan2.2-Distill-Loras",
        "path": "wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors",
    },
    {
        "filename": "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors",
        "folder": "loras",
        "repo": "lightx2v/Wan2.2-Distill-Loras",
        "path": "wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors",
    },
]
REMOTE = "comfybox:/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/"


def main() -> int:
    cfg = load_config()
    lora_dir = model_dirs(cfg).get("loras")
    if not lora_dir:
        print("No loras dir in config", flush=True)
        return 1
    Path(lora_dir).mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for entry in ENTRIES:
        path = download_asset(cfg, entry, force=False)
        print(f"OK {path} ({path.stat().st_size // 1024 // 1024} MB)", flush=True)
        saved.append(path)

    print("SCP → ComfyBox…", flush=True)
    cmd = ["scp", "-o", "BatchMode=yes", *[str(p) for p in saved], REMOTE]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.stdout:
        print(proc.stdout[-2000:], flush=True)
    if proc.stderr:
        print(proc.stderr[-2000:], flush=True)
    if proc.returncode != 0:
        print("SCP failed — files are local; sync manually if needed", flush=True)
        return 2
    print("DONE — restart or refresh ComfyUI model list if LoRAs not visible yet", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

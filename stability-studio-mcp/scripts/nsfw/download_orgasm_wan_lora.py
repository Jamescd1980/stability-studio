"""Download Wan 2.2 I2V Orgasm HIGH/LOW → local SM Lora/ + scp to ComfyBox."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from huggingface_hub import hf_hub_download  # noqa: E402
from studio.config import load_config  # noqa: E402
from studio.wan_assets import model_dirs  # noqa: E402

REPO = "iarcanar/wan22_template"
FILES = [
    (
        "Wan2.2 - I2V - Orgasm - HIGH 14B.safetensors",
        "Wan22-I2V-Orgasm-HIGH-14B.safetensors",
    ),
    (
        "Wan2.2 - I2V - Orgasm - LOW 14B.safetensors",
        "Wan22-I2V-Orgasm-LOW-14B.safetensors",
    ),
]
REMOTE = "comfybox:/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/"


def main() -> int:
    cfg = load_config()
    lora_dir = model_dirs(cfg).get("loras")
    if not lora_dir:
        print("No loras dir in config", flush=True)
        return 1
    lora_dir = Path(lora_dir)
    lora_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for remote_name, local_name in FILES:
        dest = lora_dir / local_name
        if dest.is_file() and dest.stat().st_size > 100_000_000:
            print(f"SKIP {dest.name}", flush=True)
            saved.append(dest)
            continue
        print(f"DL {remote_name}…", flush=True)
        path = hf_hub_download(repo_id=REPO, filename=remote_name, local_dir=str(lora_dir / "_hf_tmp"))
        src = Path(path)
        shutil.copy2(src, dest)
        print(f"OK {dest} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)
        saved.append(dest)

    print("SCP → ComfyBox…", flush=True)
    cmd = ["scp", "-o", "BatchMode=yes", *[str(p) for p in saved], REMOTE]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    print(proc.stdout[-2000:] if proc.stdout else "", flush=True)
    print(proc.stderr[-2000:] if proc.stderr else "", flush=True)
    if proc.returncode != 0:
        print("SCP failed — files are local; sync manually if needed", flush=True)
        return 2
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

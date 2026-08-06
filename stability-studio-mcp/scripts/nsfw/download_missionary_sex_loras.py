# -*- coding: utf-8 -*-
"""Download Wan2.2 I2V Missionary Sex HIGH/LOW into SM Lora/ (shared with comfybox)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import requests

DEST = Path(r"D:\StabilityMatrix-win-x64\Data\Models\Lora")
DEST.mkdir(parents=True, exist_ok=True)

BASE = "https://huggingface.co/tianbugao/wan_i2v/resolve/main/loras"
FILES = [
    (
        f"{BASE}/Wan2.2%20-%20I2V%20-%20Missionary%20Sex%20-%20HIGH%2014B.safetensors",
        "Wan2.2 - I2V - Missionary Sex - HIGH 14B.safetensors",
    ),
    (
        f"{BASE}/Wan2.2%20-%20I2V%20-%20Missionary%20Sex%20-%20LOW%2014B.safetensors",
        "Wan2.2 - I2V - Missionary Sex - LOW 14B.safetensors",
    ),
]


def fetch(url: str, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 100_000_000:
        print(f"skip exists {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)
        return
    print(f"GET {dest.name} ...", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=600, allow_redirects=True) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(dest)
    print(f"ok {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)


def verify_remote(name: str) -> None:
    # Game drive is visible on comfybox at /mnt/game/...
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "comfybox",
        f"ls -lh '/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/{name}'",
    ]
    print("verify:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=False)


def main() -> int:
    print("dest", DEST, flush=True)
    for url, name in FILES:
        fetch(url, DEST / name)
        verify_remote(name)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""Download dtwr434 Wan 2.2 I2V POV Missionary HIGH+LOW into SM Lora/ (shared with comfybox)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(r"D:\StabilityMatrix-win-x64\Data\Models\Lora")
DEST.mkdir(parents=True, exist_ok=True)

cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
HEADERS = {
    "Authorization": f"Bearer {cfg['civitai']['api_key']}",
    "User-Agent": "onedesk-mcp",
}

DOWNLOADS = [
    (
        "https://civitai.com/api/download/models/2098405",
        "wan2.2_i2v_highnoise_pov_missionary_v1.0.safetensors",
    ),
    (
        "https://civitai.com/api/download/models/2098396",
        "wan2.2_i2v_lownoise_pov_missionary_v1.0.safetensors",
    ),
]


def fetch(url: str, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 100_000_000:
        print(f"skip exists {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)
        return
    print(f"GET {dest.name} ...", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers=HEADERS, stream=True, timeout=600, allow_redirects=True) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(dest)
    print(f"ok {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)


def verify_remote(name: str) -> None:
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
    for url, name in DOWNLOADS:
        fetch(url, DEST / name)
        verify_remote(name)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""Run on comfybox: download BJ Wan 2.2 I2V LoRAs into Game-drive Lora/."""
from __future__ import annotations

import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

DEST = Path("/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora")
KEY = Path("/tmp/civitai_key").read_text(encoding="utf-8").strip()

DOWNLOADS = [
    ("https://civitai.com/api/download/models/2484657", "wan22-k3nk4llinon3-16epoc-full-high-k3nk.safetensors"),
    ("https://civitai.com/api/download/models/2538990", "wan22-k3nk4llinon3-15epoc-full-low-k3nk.safetensors"),
    ("https://civitai.com/api/download/models/2325788", "wan22-ultimatedeepthroat-i2v-102epoc-high-k3nk.safetensors"),
    ("https://civitai.com/api/download/models/2191446", "wan22-ultimatedeepthroat-I2V-101epoc-low-k3nk.safetensors"),
    ("https://civitai.com/api/download/models/2121297", "wan2.2-i2v-oral-insertion-v1.0.zip"),
]


def fetch(url: str, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"skip {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)
        return
    print(f"GET {dest.name} ...", flush=True)
    req = Request(url, headers={"Authorization": f"Bearer {KEY}"})
    with urlopen(req, timeout=600) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"ok {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    print("dest", DEST, flush=True)
    for url, name in DOWNLOADS:
        dest = DEST / name
        fetch(url, dest)
        if name.endswith(".zip") and dest.is_file():
            with zipfile.ZipFile(dest) as zf:
                for info in zf.infolist():
                    if not info.filename.lower().endswith(".safetensors"):
                        continue
                    out = DEST / Path(info.filename).name
                    if out.is_file() and out.stat().st_size > 1_000_000:
                        print(f"  skip {out.name}", flush=True)
                        continue
                    out.write_bytes(zf.read(info))
                    print(f"  wrote {out.name} ({out.stat().st_size // 1024 // 1024} MB)", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

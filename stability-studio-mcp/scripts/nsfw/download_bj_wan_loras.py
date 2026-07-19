# -*- coding: utf-8 -*-
"""Download Wan 2.2 I2V BJ/oral LoRAs into SM Lora/ (Game drive via Windows path if present)."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import requests
import yaml

cfg = yaml.safe_load(
    Path(r"D:/studio-agent/stability-studio-mcp/config.yaml").read_text(encoding="utf-8")
)
key = cfg["civitai"]["api_key"]
headers = {"Authorization": f"Bearer {key}"}

# Prefer Game-drive SM if mounted from Windows; else local SM.
candidates = [
    Path(r"D:/StabilityMatrix-win-x64/Data/Models/Lora"),
]
dest_root = next((p for p in candidates if p.exists()), candidates[0])
dest_root.mkdir(parents=True, exist_ok=True)

# HIGH/LOW pairs for Wan2.2 I2V-A14B (+ oral insertion zip)
DOWNLOADS = [
    # K3NK NSFW helper — general anatomy / NSFW motion assist
    ("https://civitai.com/api/download/models/2484657", "wan22-k3nk4llinon3-16epoc-full-high-k3nk.safetensors"),
    ("https://civitai.com/api/download/models/2538990", "wan22-k3nk4llinon3-15epoc-full-low-k3nk.safetensors"),
    # Ultimate DeepThroat I2V — oral persistence (same author as your fullnelson LoRA)
    ("https://civitai.com/api/download/models/2325788", "wan22-ultimatedeepthroat-i2v-102epoc-high-k3nk.safetensors"),
    ("https://civitai.com/api/download/models/2191446", "wan22-ultimatedeepthroat-I2V-101epoc-low-k3nk.safetensors"),
    # Oral Insertion — zip may contain high/low
    ("https://civitai.com/api/download/models/2121297", "wan2.2-i2v-oral-insertion-v1.0.zip"),
]


def fetch(url: str, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"skip exists {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)
        return
    print(f"GET {dest.name} ...", flush=True)
    with requests.get(url, headers=headers, stream=True, timeout=600, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
    print(f"ok {dest.name} ({dest.stat().st_size // 1024 // 1024} MB)", flush=True)


def main() -> None:
    print("dest", dest_root, flush=True)
    for url, name in DOWNLOADS:
        dest = dest_root / name
        fetch(url, dest)
        if name.endswith(".zip") and dest.is_file():
            print(f"extract {name}", flush=True)
            with zipfile.ZipFile(dest) as zf:
                for info in zf.infolist():
                    if not info.filename.lower().endswith(".safetensors"):
                        continue
                    out = dest_root / Path(info.filename).name
                    if out.is_file() and out.stat().st_size > 1_000_000:
                        print(f"  skip {out.name}", flush=True)
                        continue
                    out.write_bytes(zf.read(info))
                    print(f"  wrote {out.name} ({out.stat().st_size // 1024 // 1024} MB)", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

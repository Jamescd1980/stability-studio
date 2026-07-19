# -*- coding: utf-8 -*-
"""Download ZH Glow Eyes + Wet Skin IL + Dlang Detailed Eyes; sync to ComfyBox."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
KEY = (cfg.get("civitai") or {}).get("api_key") or ""
HEADERS = {"Authorization": f"Bearer {KEY}"}

LOCAL = Path(r"D:\StabilityMatrix-win-x64\Data\Models\Lora")
EXTRA = Path(r"D:\Extra Models") / "LoRa's"
REMOTE = "comfybox:/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/"

TARGETS = [
    {
        "id": "zh_glow_eyes",
        "version_id": 2709158,
        "filename": "ZH_GlowEyes_IL.safetensors",
        "trigger": "ZH_Glow3y3s, glowing, glowing eyes",
        "use": "001/002/005 specialty glow eyes",
        "weight": "0.6–1.2",
    },
    {
        "id": "wet_skin_il",
        "version_id": 1465593,
        "filename": "SweatyStyle_WetSkin_IL.safetensors",
        "trigger": "SweatyStyle (+ wet, shiny skin, glistening skin)",
        "use": "006/007 wet glossy skin",
        "weight": "0.8–1.0",
    },
    {
        "id": "dlang_detailed_eyes",
        "version_id": 1764525,
        "filename": "Dlang_DetailedEyes_IL.safetensors",
        "trigger": "detailed eyes, magic eyes, soft shimmer on the iris",
        "use": "iris shimmer / crystalline detail",
        "weight": "0.6–0.9",
    },
]


def download(version_id: int, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"skip {dest.name} ({dest.stat().st_size})", flush=True)
        return dest
    url = f"https://civitai.com/api/download/models/{version_id}"
    print(f"GET {dest.name} <- {url}", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers=HEADERS, stream=True, timeout=600, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if total and done % (50 * 1024 * 1024) < len(chunk):
                    print(f"  ... {done // (1024 * 1024)} / {total // (1024 * 1024)} MB", flush=True)
    tmp.replace(dest)
    print(f"ok {dest.name} {dest.stat().st_size}", flush=True)
    return dest


def main() -> None:
    if not KEY:
        raise SystemExit("Missing civitai.api_key")
    paths = []
    EXTRA.mkdir(parents=True, exist_ok=True)
    for t in TARGETS:
        dest = LOCAL / t["filename"]
        download(int(t["version_id"]), dest)
        paths.append(dest)
        extra = EXTRA / t["filename"]
        if not extra.is_file() or extra.stat().st_size != dest.stat().st_size:
            extra.write_bytes(dest.read_bytes())
            print(f"copied Extra {extra.name}", flush=True)

    print("SCP -> ComfyBox…", flush=True)
    subprocess.run(
        ["scp", "-o", "BatchMode=yes", *[str(p) for p in paths], REMOTE],
        check=True,
    )
    subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "comfybox",
            "ls -lh /mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/ZH_GlowEyes_IL.safetensors "
            "/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/SweatyStyle_WetSkin_IL.safetensors "
            "/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/Dlang_DetailedEyes_IL.safetensors",
        ],
        check=False,
    )
    manifest = {"ok": True, "loras": TARGETS, "local": str(LOCAL), "remote": REMOTE}
    out = ROOT / "outputs" / "eye_water_loras_installed.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("WROTE", out, flush=True)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Download Taz PENISLORA Wan 2.2 I2V HIGH/LOW from HuggingFace mirror → SM + comfybox."""
from __future__ import annotations

import subprocess
from pathlib import Path

import requests

DEST = Path(r"D:/StabilityMatrix-win-x64/Data/Models/Lora")
DEST.mkdir(parents=True, exist_ok=True)

# Newer epochs from UnifiedHorusRA mirror of Taz I2V-A14B
BASE = (
    "https://huggingface.co/UnifiedHorusRA/TheWan2.2I2V/resolve/main/"
    "Penis_Lora_Blowjob_Cumshot_Taz_-_WAN_2_2_14b_5B_1_3b_T2V__I2V_Wan_2_1__2_2/"
    "Wan_Video_2_2_I2V-A14B"
)
FILES = [
    (f"{BASE}/PENISLORA_22_i2v_HIGH_e320.safetensors", "PENISLORA_wan22_i2v_high.safetensors"),
    (f"{BASE}/PENISLORA_22_i2v_LOW_e496.safetensors", "PENISLORA_wan22_i2v_low.safetensors"),
]


def main() -> None:
    paths = []
    for url, name in FILES:
        out = DEST / name
        paths.append(out)
        if out.is_file() and out.stat().st_size > 1_000_000:
            print(f"skip {name}", flush=True)
            continue
        print(f"GET {name}", flush=True)
        with requests.get(url, stream=True, timeout=600, allow_redirects=True) as r:
            r.raise_for_status()
            tmp = out.with_suffix(".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
            tmp.replace(out)
        print(f"ok {name} {out.stat().st_size}", flush=True)

    subprocess.run(
        ["scp", *[str(p) for p in paths], "comfybox:/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/"],
        check=True,
    )
    subprocess.run(
        ["ssh", "comfybox", "ls -la /mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/PENISLORA*"],
        check=True,
    )
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import re
import subprocess
from pathlib import Path

import requests
import yaml

cfg = yaml.safe_load(
    Path(r"D:/studio-agent/stability-studio-mcp/config.yaml").read_text(encoding="utf-8")
)
key = cfg["civitai"]["api_key"]
headers = {"Authorization": f"Bearer {key}"}
dest = Path(r"D:/StabilityMatrix-win-x64/Data/Models/Lora")
dest.mkdir(parents=True, exist_ok=True)

FILES = [
    ("https://civitai.com/api/download/models/2772088", "CloseUpFacialCum-v10_High.safetensors"),
    ("https://civitai.com/api/download/models/2772322", "CloseUpFacialCum-v10_Low.safetensors"),
]


def main() -> None:
    paths = []
    for url, name in FILES:
        out = dest / name
        paths.append(out)
        if out.is_file() and out.stat().st_size > 1_000_000:
            print(f"skip {name}", flush=True)
            continue
        print(f"GET {name}", flush=True)
        with requests.get(url, headers=headers, stream=True, timeout=600, allow_redirects=True) as r:
            r.raise_for_status()
            tmp = out.with_suffix(".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
            tmp.replace(out)
        print(f"ok {name} {out.stat().st_size}", flush=True)

    # sync to comfybox Game drive
    cmd = [
        "scp",
        *[str(p) for p in paths],
        "comfybox:/mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/",
    ]
    print("SCP", cmd, flush=True)
    subprocess.run(cmd, check=True)
    subprocess.run(
        ["ssh", "comfybox", "ls -la /mnt/game/StabilityMatrix-win-x64/Data/Models/Lora/CloseUpFacialCum*"],
        check=True,
    )


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml

cfg = yaml.safe_load(
    Path(r"D:/studio-agent/stability-studio-mcp/config.yaml").read_text(encoding="utf-8")
)
key = cfg["civitai"]["api_key"]
headers = {"Authorization": f"Bearer {key}"}

models = [
    (1465836, "Ultimate Blowjob Wan2.2"),
    (1874153, "Oral Insertion WAN 2.2"),
    (1476909, "Penis Lora Blowjob Taz"),
    (1874811, "Ultimate DeepThroat K3NK"),
    (2206794, "K3NK NSFW helper"),
]

out = []
for mid, name in models:
    r = requests.get(f"https://civitai.com/api/v1/models/{mid}", headers=headers, timeout=45)
    row = {"id": mid, "name": name, "status": r.status_code, "versions": []}
    if r.status_code != 200:
        row["error"] = r.text[:300]
        out.append(row)
        print(name, r.status_code)
        continue
    m = r.json()
    for v in m.get("modelVersions") or []:
        files = []
        for f in v.get("files") or []:
            files.append(
                {
                    "name": f.get("name"),
                    "size_mb": round((f.get("sizeKB") or 0) / 1024, 1),
                    "downloadUrl": f.get("downloadUrl"),
                }
            )
        row["versions"].append(
            {
                "id": v.get("id"),
                "name": v.get("name"),
                "baseModel": v.get("baseModel"),
                "files": files,
            }
        )
        print(
            f"{name} | {v.get('name')} | {v.get('baseModel')} | "
            f"{[x['name'] for x in files]}"
        )
    out.append(row)

Path(r"D:/studio-agent/stability-studio-mcp/outputs/bj_wan_lora_candidates.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8"
)
print("wrote outputs/bj_wan_lora_candidates.json")

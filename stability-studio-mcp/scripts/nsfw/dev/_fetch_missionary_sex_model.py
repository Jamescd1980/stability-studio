# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[3]
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
h = {"Authorization": "Bearer " + cfg["civitai"]["api_key"], "User-Agent": "onedesk-mcp"}
out = []
for mid in [1849369, 1331682, 1983608]:
    r = requests.get(f"https://civitai.com/api/v1/models/{mid}", headers=h, timeout=45)
    row = {"id": mid, "status": r.status_code}
    if r.status_code == 200:
        m = r.json()
        row["name"] = m.get("name")
        vers = []
        for v in m.get("modelVersions") or []:
            files = [
                {
                    "name": f.get("name"),
                    "sizeKB": f.get("sizeKB"),
                    "downloadUrl": f.get("downloadUrl"),
                }
                for f in (v.get("files") or [])
                if str(f.get("name", "")).endswith(".safetensors")
            ]
            if not files:
                continue
            vers.append(
                {
                    "id": v.get("id"),
                    "name": v.get("name"),
                    "baseModel": v.get("baseModel"),
                    "trainedWords": v.get("trainedWords"),
                    "files": files,
                }
            )
        row["versions"] = vers
    out.append(row)

path = ROOT / "outputs" / "missionary_sex_model_detail.json"
path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(path)
for row in out:
    print(row.get("id"), row.get("status"), row.get("name"))
    for v in row.get("versions") or []:
        print(" ", v["id"], v["name"], v["baseModel"], [f["name"] for f in v["files"]])

# -*- coding: utf-8 -*-
"""Find Wan 2.2 Missionary Sex HIGH/LOW LoRA pair on CivitAI."""
from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[3]
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
key = cfg["civitai"]["api_key"]
H = {"Authorization": f"Bearer {key}", "User-Agent": "stability-studio"}

QUERIES = [
    "Missionary Sex WAN 2.2",
    "missionary sex wan22",
    "wan 2.2 missionary sex",
    "POV Missionary Insertion WAN",
    "missionary thrusting wan 2.2",
    "wan2.2 missionary",
]


def show(m: dict) -> None:
    name = m.get("name", "")
    mid = m.get("id")
    print(f"\nMODEL {mid} | {name}")
    for v in (m.get("modelVersions") or [])[:8]:
        files = [
            {
                "name": f.get("name"),
                "sizeMB": round((f.get("sizeKB") or 0) / 1024, 1),
                "downloadUrl": f.get("downloadUrl"),
            }
            for f in (v.get("files") or [])
        ]
        print(
            f"  ver {v.get('id')} | {v.get('name')} | base={v.get('baseModel')} | "
            f"words={v.get('trainedWords')} | files={json.dumps(files, ensure_ascii=False)}"
        )


def main() -> None:
    seen: set[int] = set()
    for q in QUERIES:
        r = requests.get(
            "https://civitai.com/api/v1/models",
            headers=H,
            params={"query": q, "types": "LORA", "limit": 20, "nsfw": "true"},
            timeout=45,
        )
        print(f"=== {q} status={r.status_code}")
        if r.status_code != 200:
            print(r.text[:400])
            continue
        for m in r.json().get("items") or []:
            mid = int(m["id"])
            if mid in seen:
                continue
            name = (m.get("name") or "").lower()
            if any(
                x in name
                for x in ("mission", "sex", "insert", "thrust", "vagina", "pov")
            ):
                seen.add(mid)
                show(m)

    out = ROOT / "outputs" / "missionary_sex_lora_candidates.json"
    out.write_text(json.dumps({"queries": QUERIES, "seen": sorted(seen)}, indent=2), encoding="utf-8")
    print("DONE", out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Search Civitai for NSFW LoRAs matching Illustrious / Pony / Flux lanes."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from studio.config import load_config

QUERIES = [
    "WAI NSFW illustrious",
    "NTR MIX pony",
    "illustrious explicit",
    "pony hentai sex",
    "flux nsfw lora",
    "concept sex position pony",
]


def main() -> None:
    cfg = load_config()
    key = (cfg.get("civitai") or {}).get("api_key") or os.environ.get("CIVITAI_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    hits: list[dict] = []
    for q in QUERIES:
        r = requests.get(
            "https://civitai.com/api/v1/models",
            params={"query": q, "types": "LORA", "limit": 8, "sort": "Highest Rated"},
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        for m in r.json().get("items", []):
            v = m["modelVersions"][0]
            base = (v.get("baseModel") or "")
            files = v.get("files") or []
            fname = files[0].get("name", "") if files else ""
            size_mb = round((files[0].get("sizeKB", 0) or 0) / 1024, 1) if files else 0
            hits.append(
                {
                    "name": m["name"],
                    "model_id": m["id"],
                    "version_id": v["id"],
                    "version_name": v["name"],
                    "base_model": base,
                    "filename": fname,
                    "size_mb": size_mb,
                    "query": q,
                    "page": f"https://civitai.com/models/{m['id']}?modelVersionId={v['id']}",
                }
            )

    seen: set[int] = set()
    unique = []
    for h in hits:
        if h["version_id"] in seen:
            continue
        seen.add(h["version_id"])
        unique.append(h)

    print(json.dumps(unique[:20], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

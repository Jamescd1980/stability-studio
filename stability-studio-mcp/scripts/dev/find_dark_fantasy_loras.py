"""Search Civitai for SDXL LoRAs matching dark epic fantasy reference."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))
from _bootstrap import ROOT  # noqa: E402

from studio.config import load_config  # noqa: E402


def main() -> None:
    cfg = load_config()
    key = (cfg.get("civitai") or {}).get("api_key") or os.environ.get("CIVITAI_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    queries = [
        "dark fantasy epic",
        "cinematic concept art",
        "grimdark fantasy",
        "eldritch hellscape",
    ]
    hits: list[dict] = []
    for q in queries:
        r = requests.get(
            "https://civitai.com/api/v1/models",
            params={"query": q, "types": "LORA", "limit": 6, "sort": "Highest Rated"},
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        for m in r.json().get("items", []):
            v = m["modelVersions"][0]
            base = (v.get("baseModel") or "").lower()
            if "sdxl" not in base and "pony" not in base and "illustrious" not in base:
                continue
            files = v.get("files") or []
            size_mb = round((files[0].get("sizeKB", 0) or 0) / 1024, 1) if files else 0
            hits.append(
                {
                    "name": m["name"],
                    "model_id": m["id"],
                    "version_id": v["id"],
                    "version_name": v["name"],
                    "base_model": v.get("baseModel"),
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

    out = ROOT / "outputs" / "dark_fantasy_lora_candidates.json"
    out.write_text(json.dumps(unique[:12], indent=2), encoding="utf-8")
    print(json.dumps(unique[:12], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

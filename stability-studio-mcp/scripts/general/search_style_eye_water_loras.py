# -*- coding: utf-8 -*-
"""Search Civitai for Illustrious eye / lighting / water LoRAs (options only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
KEY = (cfg.get("civitai") or {}).get("api_key") or ""
HEADERS = {"Authorization": f"Bearer {KEY}"}

QUERIES = [
    "glowing eyes",
    "shiny eyes",
    "detailed iris",
    "heterochromia eyes illustrious",
    "water caustics",
    "underwater light",
    "wet skin",
    "shiny skin",
    "specular lighting",
    "cinematic lighting anime",
    "low key lighting",
    "neon rim light",
]


def ascii(s: str) -> str:
    return "".join(ch if ord(ch) < 128 else "?" for ch in (s or ""))


def search(q: str) -> list[dict]:
    r = requests.get(
        "https://civitai.com/api/v1/models",
        headers=HEADERS,
        params={
            "query": q,
            "types": "LORA",
            "baseModels": "Illustrious",
            "limit": 8,
            "sort": "Most Downloaded",
        },
        timeout=45,
    )
    r.raise_for_status()
    out = []
    for m in r.json().get("items") or []:
        if "Illustrious" not in (m.get("baseModels") or []):
            continue
        vers = m.get("modelVersions") or []
        if not vers:
            continue
        v = vers[0]
        files = v.get("files") or [{}]
        out.append(
            {
                "query": q,
                "model_id": m["id"],
                "name": ascii(m.get("name") or ""),
                "downloads": (m.get("stats") or {}).get("downloadCount"),
                "version_id": v.get("id"),
                "filename": ascii((files[0] or {}).get("name") or ""),
                "triggers": [ascii(t) for t in (v.get("trainedWords") or [])[:4]],
                "url": f"https://civitai.com/models/{m['id']}",
            }
        )
    return out


def main() -> None:
    if not KEY:
        raise SystemExit("no civitai key")
    seen: set[int] = set()
    rows: list[dict] = []
    for q in QUERIES:
        print(f"=== {q}", flush=True)
        try:
            hits = search(q)
        except Exception as exc:
            print(f"  ERR {exc}", flush=True)
            continue
        for h in hits:
            mid = h["model_id"]
            mark = "" if mid not in seen else " (dup)"
            seen.add(mid)
            print(
                f"  {h['downloads']:>7}  id={mid} v={h['version_id']}  {h['name'][:58]}{mark}",
                flush=True,
            )
            if mark:
                continue
            rows.append(h)

    # Dedup rank by downloads
    rows.sort(key=lambda x: int(x.get("downloads") or 0), reverse=True)
    # Bucket by likely use
    buckets = {"eyes": [], "water_wet": [], "lighting": [], "other": []}
    for r in rows:
        blob = (r["name"] + " " + r["query"] + " " + " ".join(r["triggers"])).lower()
        if any(k in blob for k in ("eye", "iris", "pupil", "gaze")):
            buckets["eyes"].append(r)
        elif any(k in blob for k in ("water", "wet", "caustic", "underwater", "ocean")):
            buckets["water_wet"].append(r)
        elif any(k in blob for k in ("light", "neon", "rim", "cinematic", "shadow", "specular", "gloss", "shiny skin")):
            buckets["lighting"].append(r)
        else:
            buckets["other"].append(r)

    out = {
        "have_already": [
            "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
            "Loraeyes_V1.safetensors",
            "constricted_pupils_v0.2a.safetensors",
            "DramaticColor_IL_v1.safetensors",
            "LensFlare_LightLeak_IL.safetensors (Prism Light)",
            "ILDetailerV2.safetensors / hyperdetailer_v095",
            "wan22-light-volumetric.safetensors (video, not stills)",
        ],
        "checkpoints_relevant": [
            "waijfu_alpha.safetensors (current)",
            "waiIllustriousSDXL_v170.safetensors",
            "n4mik4ILSFWNSFW_v20.safetensors (neon/hero; NSFW bleed risk)",
            "perfection25DILXLIllustrious_33.safetensors (glossier 2.5D)",
            "divineelegancemix_V10.safetensors (glamour lean)",
        ],
        "candidates": {k: v[:12] for k, v in buckets.items()},
        "top_overall": rows[:20],
    }
    path = ROOT / "outputs" / "style_eye_water_lora_options.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nWROTE", path, flush=True)
    print("\n--- TOP EYES ---", flush=True)
    for r in buckets["eyes"][:8]:
        print(f"  {r['downloads']}  {r['name']}  {r['url']}", flush=True)
    print("\n--- TOP WATER/WET ---", flush=True)
    for r in buckets["water_wet"][:8]:
        print(f"  {r['downloads']}  {r['name']}  {r['url']}", flush=True)
    print("\n--- TOP LIGHTING ---", flush=True)
    for r in buckets["lighting"][:8]:
        print(f"  {r['downloads']}  {r['name']}  {r['url']}", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Export character_list.json + show_index.json for Myra pre-guide (from catalog.yaml)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog.yaml"
OUT_DIR = Path(r"D:\studio-agent\handoff\myra-patches\cast")

# Cast without series: in catalog → assign here for show_index.
DEFAULT_SERIES = {
    "fern": "frieren",
    "frieren": "frieren",
    "ubel": "frieren",
    "flamme": "frieren",
}

SHOW_ALIASES = {
    "frieren": [
        "frieren",
        "sousou no frieren",
        "grimoire of desires",
        "grimoire",
        "frieren beyond journey's end",
    ],
    "solo_leveling": [
        "solo leveling",
        "solo_leveling",
        "ore dake level up na ken",
        "sung jinwoo show",
    ],
}


def _gender(meta: dict) -> str:
    g = str(meta.get("gender") or "").strip().lower()
    if g in {"female", "male", "mixed"}:
        return g
    helpers = str(meta.get("caption_helpers") or "").lower()
    trigger = str(meta.get("trigger") or "").lower()
    blob = helpers + " " + trigger
    if "1boy" in blob or "man" == helpers:
        return "male"
    return "female"


def _display_name(cid: str, meta: dict) -> str:
    if meta.get("display_name"):
        return str(meta["display_name"])
    # Park Heejin from park_heejin
    return cid.replace("_", " ").title()


def main() -> int:
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8")) or {}
    block = data.get("character_loras") or {}
    characters: list[dict] = []
    shows: dict[str, dict] = {}

    for cid, meta in block.items():
        if not isinstance(meta, dict):
            continue
        series = str(meta.get("series") or DEFAULT_SERIES.get(cid) or "misc").strip()
        aliases = [str(a) for a in (meta.get("aliases") or [])]
        # Help STT: space form of id + common mangling
        aliases.append(cid.replace("_", " "))
        if cid == "park_heejin":
            aliases.extend(["hejin park", "hejin", "park hejin", "heejin park"])
        if cid == "fern":
            aliases.append("firm")  # STT
        row = {
            "id": cid,
            "display_name": _display_name(cid, meta),
            "aliases": sorted({a.lower() for a in aliases if a}),
            "series": series,
            "gender": _gender(meta),
            "trigger": meta.get("trigger"),
            "file": meta.get("file"),
            "weight": float(meta.get("weight", 0.8)),
            "preferred_style": meta.get("preferred_style") or "waijfu",
            "pair_with": list(meta.get("pair_with") or []),
            "caption_helpers": meta.get("caption_helpers") or "",
        }
        characters.append(row)
        shows.setdefault(
            series,
            {
                "id": series,
                "aliases": list(SHOW_ALIASES.get(series, [series.replace("_", " ")])),
                "characters": [],
            },
        )
        shows[series]["characters"].append(cid)

    characters.sort(key=lambda x: x["id"])
    show_list = []
    for sid, smeta in sorted(shows.items()):
        aliases = [a.lower() for a in smeta["aliases"]]
        aliases.append(sid.replace("_", " "))
        show_list.append(
            {
                "id": sid,
                "aliases": sorted(set(aliases)),
                "characters": sorted(smeta["characters"]),
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "character_list.json").write_text(
        json.dumps({"characters": characters}, indent=2) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "show_index.json").write_text(
        json.dumps({"shows": show_list}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(characters)} characters, {len(show_list)} shows -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

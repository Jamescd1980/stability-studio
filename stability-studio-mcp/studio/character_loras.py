"""Trained character LoRAs (Frieren cast + Solo Leveling) for generate_image(loras=…)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _catalog_block(catalog_data: dict[str, Any]) -> dict[str, Any]:
    return dict(catalog_data.get("character_loras") or {})


def list_character_loras(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cid, meta in _catalog_block(catalog_data).items():
        if not isinstance(meta, dict):
            continue
        out.append(
            {
                "id": cid,
                "file": meta.get("file"),
                "weight": float(meta.get("weight", 0.8)),
                "trigger": meta.get("trigger"),
                "preferred_style": meta.get("preferred_style") or "waijfu",
                "aliases": list(meta.get("aliases") or []),
            }
        )
    return sorted(out, key=lambda x: x["id"])


def resolve_character_id(catalog_data: dict[str, Any], character: str) -> str | None:
    key = (character or "").strip().lower().replace(" ", "_")
    if not key:
        return None
    block = _catalog_block(catalog_data)
    if key in block:
        return key
    for cid, meta in block.items():
        aliases = [str(a).lower() for a in (meta.get("aliases") or [])]
        if key in aliases or key == str(meta.get("trigger") or "").lower():
            return cid
        if key == str(meta.get("file") or "").lower().removesuffix(".safetensors"):
            return cid
    return None


def resolve_character_loras(
    catalog_data: dict[str, Any],
    character: str,
    *,
    include_eye_lora: bool = True,
) -> dict[str, Any]:
    """Return generate_image-ready loras list + trigger/style hints."""
    cid = resolve_character_id(catalog_data, character)
    if not cid:
        return {
            "ok": False,
            "error": f"Unknown character LoRA '{character}'",
            "known": [x["id"] for x in list_character_loras(catalog_data)],
        }
    meta = _catalog_block(catalog_data)[cid]
    loras: list[dict[str, Any]] = [
        {"file": meta["file"], "weight": float(meta.get("weight", 0.8))}
    ]
    if include_eye_lora:
        for pair in meta.get("pair_with") or []:
            if isinstance(pair, dict) and pair.get("file"):
                loras.append(
                    {"file": pair["file"], "weight": float(pair.get("weight", 0.8))}
                )
    return {
        "ok": True,
        "character": cid,
        "trigger": meta.get("trigger"),
        "preferred_style": meta.get("preferred_style") or "waijfu",
        "prompt_hint": (
            f"Include trigger `{meta.get('trigger')}` in the positive prompt. "
            "Preferred style=waijfu. Optional tags: perfect eyes, eye_focus."
        ),
        "loras": loras,
    }


def check_character_loras_on_disk(
    catalog_data: dict[str, Any], models_dir: Path
) -> dict[str, Any]:
    lora_root = models_dir / "Lora"
    items = []
    missing = []
    for row in list_character_loras(catalog_data):
        path = lora_root / str(row["file"])
        ok = path.is_file() and path.stat().st_size > 1024
        if ok:
            # reject NTFS zeroed shells
            head = path.open("rb").read(16)
            ok = any(b != 0 for b in head)
        entry = {**row, "path": str(path), "installed": ok}
        items.append(entry)
        if not ok:
            missing.append(row["id"])
    return {
        "ok": not missing,
        "missing": missing,
        "loras": items,
        "usage": (
            "resolve_character_loras(character='fern') then pass loras= into generate_image; "
            "put the trigger token in the positive prompt."
        ),
    }

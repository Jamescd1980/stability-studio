"""Trained character LoRAs (Frieren cast + Solo Leveling + Shooting Gallery) for generate_image(loras=…)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _catalog_block(catalog_data: dict[str, Any]) -> dict[str, Any]:
    return dict(catalog_data.get("character_loras") or {})


def list_character_mesh_assets(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Mesh / turnaround packs on ComfyBox (catalog character_mesh_assets)."""
    block = dict(catalog_data.get("character_mesh_assets") or {})
    out: list[dict[str, Any]] = []
    for mid, meta in block.items():
        if not isinstance(meta, dict):
            continue
        out.append({"id": mid, **meta})
    return sorted(out, key=lambda x: x["id"])


def get_character_mesh_asset(
    catalog_data: dict[str, Any], character: str
) -> dict[str, Any] | None:
    cid = resolve_character_id(catalog_data, character)
    if not cid:
        return None
    meshes = dict(catalog_data.get("character_mesh_assets") or {})
    if cid in meshes and isinstance(meshes[cid], dict):
        return {"id": cid, **meshes[cid]}
    meta = _catalog_block(catalog_data).get(cid) or {}
    mesh_id = meta.get("mesh_asset_id")
    if mesh_id and mesh_id in meshes and isinstance(meshes[mesh_id], dict):
        return {"id": mesh_id, **meshes[mesh_id]}
    return None


def list_character_loras(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cid, meta in _catalog_block(catalog_data).items():
        if not isinstance(meta, dict):
            continue
        row: dict[str, Any] = {
            "id": cid,
            "file": meta.get("file"),
            "weight": float(meta.get("weight", 0.8)),
            "trigger": meta.get("trigger"),
            "preferred_style": meta.get("preferred_style") or "waijfu",
            "aliases": list(meta.get("aliases") or []),
        }
        if meta.get("caption_helpers"):
            row["caption_helpers"] = meta.get("caption_helpers")
        if meta.get("outfit_helpers"):
            row["outfit_helpers"] = meta.get("outfit_helpers")
        if meta.get("series"):
            row["series"] = meta.get("series")
        if meta.get("body_prompt_rule"):
            row["body_prompt_rule"] = meta.get("body_prompt_rule")
        if meta.get("mesh_asset_id"):
            row["mesh_asset_id"] = meta.get("mesh_asset_id")
        out.append(row)
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
    hint_parts = [
        f"Include trigger `{meta.get('trigger')}` in the positive prompt.",
        "Preferred style=waijfu.",
        "Optional tags: perfect eyes, eye_focus.",
    ]
    if meta.get("caption_helpers"):
        hint_parts.append(f"Caption helpers: {meta.get('caption_helpers')}.")
    if meta.get("body_prompt_rule"):
        hint_parts.append(str(meta.get("body_prompt_rule")))
    out: dict[str, Any] = {
        "ok": True,
        "character": cid,
        "trigger": meta.get("trigger"),
        "preferred_style": meta.get("preferred_style") or "waijfu",
        "prompt_hint": " ".join(hint_parts),
        "loras": loras,
    }
    if meta.get("caption_helpers"):
        out["caption_helpers"] = meta.get("caption_helpers")
    if meta.get("body_prompt_rule"):
        out["body_prompt_rule"] = meta.get("body_prompt_rule")
    mesh = get_character_mesh_asset(catalog_data, cid)
    if mesh:
        out["mesh_source"] = mesh
    return out


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

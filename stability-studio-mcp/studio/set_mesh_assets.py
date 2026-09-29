"""Casting-couch / set mesh asset helpers for MCP."""
from __future__ import annotations

from pathlib import Path
from typing import Any


SET_ASSET_CATALOG_KEY = "set_mesh_assets"


def list_set_mesh_assets(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    block = dict(catalog_data.get(SET_ASSET_CATALOG_KEY) or {})
    out: list[dict[str, Any]] = []
    for sid, meta in block.items():
        if not isinstance(meta, dict):
            continue
        row = {"id": sid, **meta}
        # enrich with on-disk presence for key paths
        for key in ("blend", "bg_glb", "locked_plate", "solid_maps_dir", "strip_solid_blend"):
            raw = meta.get(key)
            if isinstance(raw, str) and raw:
                p = Path(raw)
                row[f"{key}_exists"] = p.is_file() if key != "solid_maps_dir" else p.is_dir()
        out.append(row)
    return sorted(out, key=lambda x: x["id"])


def get_set_mesh_asset(catalog_data: dict[str, Any], set_id: str) -> dict[str, Any] | None:
    key = (set_id or "").strip().lower().replace(" ", "_")
    block = dict(catalog_data.get(SET_ASSET_CATALOG_KEY) or {})
    if key in block and isinstance(block[key], dict):
        return {"id": key, **block[key]}
    for sid, meta in block.items():
        aliases = [str(a).lower() for a in (meta.get("aliases") or [])]
        if key in aliases:
            return {"id": sid, **meta}
    return None


def list_solid_strip_maps(catalog_data: dict[str, Any], set_id: str = "casting_couch") -> dict[str, Any]:
    meta = get_set_mesh_asset(catalog_data, set_id) or {}
    maps_dir = Path(str(meta.get("solid_maps_dir") or ""))
    beats = list(meta.get("strip_beats") or [])
    found: list[dict[str, Any]] = []
    if maps_dir.is_dir():
        for beat in beats:
            stem = str(beat.get("stem") or "")
            entry: dict[str, Any] = {"beat_id": beat.get("id"), "stem": stem, "files": {}}
            for kind in ("gray_cut", "silhouette", "depth", "pose"):
                p = maps_dir / f"{stem}_{kind}.png"
                entry["files"][kind] = {"path": str(p), "exists": p.is_file(), "size": p.stat().st_size if p.is_file() else 0}
            found.append(entry)
    return {
        "set_id": set_id,
        "solid_maps_dir": str(maps_dir) if maps_dir else None,
        "exists": maps_dir.is_dir(),
        "beats": found,
        "kit_pose_script": meta.get("pose_script"),
        "mask_prep_kit": meta.get("mask_prep_kit"),
    }

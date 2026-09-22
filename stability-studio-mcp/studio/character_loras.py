"""Trained character LoRAs (Frieren cast + Solo Leveling + Shooting Gallery) for generate_image(loras=…).

Also resolves checkpoint-baked identities (e.g. Eris Greyrat in waijfu_alpha).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _catalog_block(catalog_data: dict[str, Any]) -> dict[str, Any]:
    return dict(catalog_data.get("character_loras") or {})


def _styles_block(catalog_data: dict[str, Any]) -> dict[str, Any]:
    return dict(catalog_data.get("styles") or {})


def list_baked_in_characters(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Characters known to live inside a checkpoint (no LoRA file)."""
    out: list[dict[str, Any]] = []
    for style_id, meta in _styles_block(catalog_data).items():
        if not isinstance(meta, dict):
            continue
        baked = meta.get("baked_in_characters") or []
        if not isinstance(baked, list):
            continue
        for row in baked:
            if not isinstance(row, dict):
                continue
            out.append(
                {
                    "style": style_id,
                    "checkpoint": meta.get("checkpoint"),
                    "id": row.get("id"),
                    "names": list(row.get("names") or []),
                    "prompt_hints": row.get("prompt_hints") or "",
                    "notes": row.get("notes") or "",
                    "identity_source": "baked_in_checkpoint",
                }
            )
    return out


def resolve_baked_in_character(
    catalog_data: dict[str, Any], character: str
) -> dict[str, Any] | None:
    key = (character or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        return None
    key_compact = key.replace("_", "")
    for row in list_baked_in_characters(catalog_data):
        rid = str(row.get("id") or "").lower().replace(" ", "_")
        names = [str(n).lower() for n in (row.get("names") or [])]
        aliases = {
            rid,
            rid.replace("_", ""),
            *[n.replace(" ", "_") for n in names],
            *names,
        }
        aliases_compact = {a.replace("_", "").replace(" ", "") for a in aliases}
        if key in aliases or key_compact in aliases_compact:
            return row
        for n in names:
            n_key = n.replace(" ", "_")
            if key in n_key or n_key in key:
                return row
    return None


def list_character_mesh_assets(catalog_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Mesh / turnaround packs on GenerationHost (catalog character_mesh_assets)."""
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
    """Return generate_image-ready loras list + trigger/style hints.

    If no LoRA exists but the character is baked into waijfu (etc.), returns baked identity.
    """
    cid = resolve_character_id(catalog_data, character)
    if not cid:
        baked_only = _baked_identity_payload(
            catalog_data, character, include_eye_lora=include_eye_lora
        )
        if baked_only:
            return baked_only
        return {
            "ok": False,
            "error": f"Unknown character LoRA '{character}'",
            "known": [x["id"] for x in list_character_loras(catalog_data)],
            "baked_in_hint": (
                "If this is Eris Greyrat (or another waijfu-baked face), call "
                "lookup_character_identity — no LoRA file required."
            ),
            "known_baked_in": [
                x.get("id")
                for x in list_baked_in_characters(catalog_data)
                if x.get("id") != "popular_anime_cast"
            ],
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
        "identity_source": "character_lora",
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
    baked = resolve_baked_in_character(catalog_data, cid) or resolve_baked_in_character(
        catalog_data, character
    )
    if baked:
        out["also_baked_in"] = baked
        out["stacking_note"] = (
            "Also baked into checkpoint — consider lower LoRA weight if overcooked "
            "(Frieren on waijfu: ≤0.50)."
        )
    return out


def _baked_identity_payload(
    catalog_data: dict[str, Any],
    character: str,
    *,
    include_eye_lora: bool,
) -> dict[str, Any] | None:
    baked = resolve_baked_in_character(catalog_data, character)
    if not baked:
        return None
    style = baked.get("style") or "waijfu"
    hints = baked.get("prompt_hints") or ""
    names = baked.get("names") or [character]
    name = names[0] if names else character
    eye = (
        [
            {
                "file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
                "weight": 0.75,
            },
            {"file": "ILDetailerV2.safetensors", "weight": 0.65},
        ]
        if include_eye_lora
        else []
    )
    return {
        "ok": True,
        "identity_source": "baked_in_checkpoint",
        "character": baked.get("id") or character,
        "names": names,
        "preferred_style": style,
        "checkpoint": baked.get("checkpoint"),
        "loras": eye,
        "trigger": None,
        "prompt_hint": (
            f"No dedicated LoRA — identity is baked into {style}. "
            f"Prompt the name `{name}` plus distinctive tags"
            + (f" ({hints})" if hints else "")
            + ". Use gold_standard Eyes+ILDetailer LoRAs for finish."
        ),
        "notes": baked.get("notes"),
        "usage": (
            f"generate_image(style='{style}', loras=<eyes/detail optional>, "
            f"prompt includes '{name}' and costume/scene tags)."
        ),
    }


def lookup_character_identity(
    catalog_data: dict[str, Any], character: str, *, include_eye_lora: bool = True
) -> dict[str, Any]:
    """Unified: dedicated LoRA if present, else baked-in checkpoint identity."""
    return resolve_character_loras(
        catalog_data, character, include_eye_lora=include_eye_lora
    )


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
        "baked_in": list_baked_in_characters(catalog_data),
        "usage": (
            "resolve_character_loras / lookup_character_identity then generate_image; "
            "Eris Greyrat is baked into waijfu (no LoRA file)."
        ),
    }

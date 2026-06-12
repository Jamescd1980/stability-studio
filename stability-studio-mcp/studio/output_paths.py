"""Shared delivery folder for MOSS audio, Wan2GP video, and agent handoff."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from studio.project_layout import ensure_project_layout, project_paths


def delivery_dir(cfg: dict[str, Any]) -> Path | None:
    raw = (cfg.get("outputs") or {}).get("delivery")
    if not raw:
        return None
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def delivery_temp_dir(cfg: dict[str, Any]) -> Path | None:
    """Raw Wan2GP / MOSS saves land here until promoted to a canonical folder."""
    paths = project_paths(cfg)
    if paths is not None:
        paths["temp"].mkdir(parents=True, exist_ok=True)
        return paths["temp"]
    root = delivery_dir(cfg)
    if root is None:
        return None
    temp = root / "temp"
    temp.mkdir(parents=True, exist_ok=True)
    return temp


def deliver_files(
    cfg: dict[str, Any],
    saved: list[str],
    *,
    bucket: str = "temp",
) -> tuple[list[str], list[str]]:
    """Copy saved files into the delivery project (default: temp/).

    Avoids _2/_3 duplicates when the source is already in the destination folder.
    Use promote_file() to move temp outputs to clips/images/audio with a fixed name.
    """
    paths = project_paths(cfg)
    if paths is not None and bucket in paths:
        dest_root = paths[bucket]
    else:
        dest_root = delivery_dir(cfg)
    if dest_root is None:
        return saved, []

    dest_root.mkdir(parents=True, exist_ok=True)
    delivered: list[str] = []
    for src in saved:
        src_path = Path(src).resolve()
        if not src_path.is_file():
            continue
        try:
            src_path.relative_to(dest_root.resolve())
            delivered.append(str(src_path))
            continue
        except ValueError:
            pass
        dest = dest_root / src_path.name
        if dest.resolve() == src_path:
            delivered.append(str(dest))
            continue
        shutil.copy2(src_path, dest)
        delivered.append(str(dest))
    return saved, delivered


def promote_file(
    src: Path,
    dest: Path,
    *,
    move: bool = True,
) -> Path:
    """Move or copy an approved temp file to its canonical project path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if move:
        if dest.is_file():
            dest.unlink()
        shutil.move(str(src), str(dest))
    else:
        shutil.copy2(src, dest)
    return dest


def write_project_log(cfg: dict[str, Any], name: str, payload: dict[str, Any]) -> Path:
    """Write JSON log to project logs/ and MCP outputs/."""
    mcp_root = Path(cfg.get("_root") or Path(__file__).resolve().parents[1])
    text = json.dumps(payload, indent=2)
    paths = project_paths(cfg)
    targets: list[Path] = [mcp_root / "outputs" / name]
    if paths is not None:
        targets.append(paths["logs"] / name)
    written = targets[0]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written = target
    return written


def sync_wan2gp_save_paths(cfg: dict[str, Any]) -> dict[str, Any]:
    """Point Wan2GP wgp_config.json save paths at delivery temp/ when set."""
    ensure_project_layout(cfg)
    dest = delivery_temp_dir(cfg)
    root = Path(cfg.get("wan2gp", {}).get("root") or "")
    if dest is None or not root.is_dir():
        return {"applied": False, "reason": "delivery or wan2gp.root not configured"}

    config_path = root / "wgp_config.json"
    if not config_path.is_file():
        return {"applied": False, "reason": f"missing {config_path}"}

    delivery = str(dest).replace("\\", "/")
    with config_path.open(encoding="utf-8") as f:
        data = json.load(f)

    keys = ("save_path", "image_save_path", "audio_save_path")
    changed = {key: data.get(key) for key in keys if data.get(key) != delivery}
    if not changed:
        return {"applied": True, "path": delivery, "changed": False}

    for key in keys:
        data[key] = delivery
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")
    return {"applied": True, "path": delivery, "changed": True, "previous": changed}

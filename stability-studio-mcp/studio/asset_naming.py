"""Asset naming helpers — shared CreateBrain / Coder convention."""

from __future__ import annotations

import re
from typing import Any


def _slug(s: str) -> str:
    t = (s or "").strip().lower().replace(" ", "_").replace("-", "_")
    t = re.sub(r"[^a-z0-9_]+", "", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def suggest_asset_name(
    project: str,
    scene: str,
    beat: str,
    view: str,
    stage: str,
    *,
    ext: str = "png",
    kind: str = "still",
) -> dict[str, Any]:
    """Build {project}_{scene}_{beat}_{view}_{stage}.{ext}."""
    parts = {
        "project": _slug(project),
        "scene": _slug(scene),
        "beat": _slug(beat),
        "view": _slug(view),
        "stage": _slug(stage),
    }
    missing = [k for k, v in parts.items() if not v]
    if missing:
        return {"ok": False, "error": f"missing parts: {missing}"}
    e = (ext or "png").lstrip(".").lower()
    if kind.lower() in {"video", "clip", "mp4"} and e == "png":
        e = "mp4"
    name = "{project}_{scene}_{beat}_{view}_{stage}.{ext}".format(**parts, ext=e)
    delivery_root = (
        r"D:\GenerationHost Images and Videos\Video"
        if e in {"mp4", "webm", "mkv", "mov"}
        else r"D:\GenerationHost Images and Videos\Images"
    )
    return {
        "ok": True,
        "filename": name,
        "stem": name.rsplit(".", 1)[0],
        "ext": e,
        "suggested_delivery_path": f"{delivery_root}\\{name}",
        "scheme": "{project}_{scene}_{beat}_{view}_{stage}.{ext}",
        "parts": parts,
        "paths_doc": r"D:\studio-agent\ollama\coder\PATHS.md",
        "handoff": r"D:\Bad boy\TheaterJobs\staging\handoff.md",
    }

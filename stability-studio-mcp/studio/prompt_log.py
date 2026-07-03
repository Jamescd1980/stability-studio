"""Image / video prompt log — searchable history per delivery project."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROMPT_LOG_FILE = "prompt_log.jsonl"


def prompt_log_path(project_root: Path) -> Path:
    return project_root / "logs" / PROMPT_LOG_FILE


def append_prompt_log(project_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    path = prompt_log_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **entry,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def read_prompt_log(
    project_root: Path,
    *,
    limit: int = 50,
    scene_id: str = "",
    style: str = "",
    kind: str = "",
) -> list[dict[str, Any]]:
    path = prompt_log_path(project_root)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if scene_id and row.get("scene_id") != scene_id:
            continue
        if style and row.get("style") != style:
            continue
        if kind and row.get("kind") != kind:
            continue
        rows.append(row)
    return rows[-limit:]


def log_from_generation_result(
    project_root: Path,
    *,
    agent: str = "mcp",
    scene_id: str = "",
    kind: str = "image",
    result: dict[str, Any],
    notes: str = "",
) -> dict[str, Any] | None:
    """Record a successful or failed generation into prompt_log.jsonl."""
    saved = result.get("saved_files") or []
    entry = {
        "agent": agent,
        "kind": kind,
        "scene_id": scene_id,
        "style": result.get("style", ""),
        "checkpoint": result.get("checkpoint", ""),
        "platform": result.get("architecture") or result.get("style", ""),
        "prompt_positive": result.get("prompt", ""),
        "prompt_negative": result.get("negative_prompt", ""),
        "width": result.get("width"),
        "height": result.get("height"),
        "steps": result.get("steps"),
        "cfg": result.get("cfg"),
        "sampler": result.get("sampler"),
        "face_detail": result.get("face_detail"),
        "output_files": saved,
        "prompt_id": result.get("prompt_id"),
        "status": "ok" if saved else "failed",
        "notes": notes,
    }
    if not entry["prompt_positive"] and not notes:
        return None
    return append_prompt_log(project_root, entry)


def log_prompt_only(
    project_root: Path,
    *,
    agent: str = "jan",
    scene_id: str = "",
    platform: str = "",
    style: str = "",
    prompt_positive: str = "",
    prompt_negative: str = "",
    source_image: str = "",
    notes: str = "",
    chapter: int | None = None,
) -> dict[str, Any]:
    """Brainstorm / prompt-only row — no GPU run yet."""
    return append_prompt_log(
        project_root,
        {
            "agent": agent,
            "kind": "prompt_only",
            "scene_id": scene_id,
            "chapter": chapter,
            "platform": platform,
            "style": style,
            "prompt_positive": prompt_positive,
            "prompt_negative": prompt_negative,
            "source_image": source_image,
            "status": "prompt_only",
            "notes": notes,
        },
    )

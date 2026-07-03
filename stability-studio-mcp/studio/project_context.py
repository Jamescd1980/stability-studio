"""Project context backlog — cross-agent handoff (Cursor, OI, Jan, human)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTEXT_VERSION = 1
CONTEXT_FILE = "project_context.json"
BACKLOG_FILE = "agent_backlog.jsonl"

DEFAULT_PHASES = (
    "setup",
    "chapter_storyboard",
    "prompt_writing",
    "image_generation",
    "video_generation",
    "audio_generation",
    "renpy_export",
    "beta_test",
    "chapter_complete",
)


def context_path(project_root: Path) -> Path:
    return project_root / "logs" / CONTEXT_FILE


def backlog_path(project_root: Path) -> Path:
    return project_root / "logs" / BACKLOG_FILE


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_context(
    *,
    project_name: str = "",
    book_title: str = "",
    active_chapter: int = 1,
) -> dict[str, Any]:
    return {
        "context_version": CONTEXT_VERSION,
        "updated": _now(),
        "project_name": project_name,
        "book_title": book_title,
        "goal": "Book → VN chapter-by-chapter; local generation via Stability Studio MCP.",
        "phase": "setup",
        "active_chapter": active_chapter,
        "active_sheet": f"storyboard/ch{active_chapter:02d}_storyboard.csv",
        "delivery_root": "",
        "character_bible": {},
        "style_defaults": {"still": "ilustmix", "hero_video": "i2v_5b_painter", "voice": "moss_voice_design"},
        "hardware_notes": "16 GB VRAM — unload Jan/LM Studio before ComfyUI generate; face_detail=false unless needed.",
        "blockers": [],
        "next_actions": [],
        "pointers": {
            "storyboard_sheet": "storyboard/ch01_storyboard.csv",
            "prompt_log": "logs/prompt_log.jsonl",
            "agent_backlog": "logs/agent_backlog.jsonl",
            "book_pdf": "source/",
            "rin_reference": "images/Rin_kitsune_approved.png",
            "docs": "STORYBOARD-SHEET.md in studio-agent repo",
        },
        "agents": {
            "cursor": {"last_seen": "", "last_summary": ""},
            "open_interpreter": {"last_seen": "", "last_summary": ""},
            "jan": {"last_seen": "", "last_summary": ""},
            "human": {"last_seen": "", "last_summary": ""},
        },
    }


def load_context(project_root: Path) -> dict[str, Any]:
    path = context_path(project_root)
    if not path.is_file():
        raise FileNotFoundError(
            f"Project context not found: {path}. Call init_project_context first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("context_version") != CONTEXT_VERSION:
        raise ValueError(f"Unsupported context_version in {path}")
    return data


def save_context(project_root: Path, data: dict[str, Any]) -> Path:
    path = context_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["context_version"] = CONTEXT_VERSION
    data["updated"] = _now()
    data["delivery_root"] = str(project_root)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def init_context(
    project_root: Path,
    *,
    project_name: str = "",
    book_title: str = "",
    active_chapter: int = 1,
    overwrite: bool = False,
) -> dict[str, Any]:
    path = context_path(project_root)
    if path.is_file() and not overwrite:
        return load_context(project_root)
    data = default_context(
        project_name=project_name or project_root.name,
        book_title=book_title,
        active_chapter=active_chapter,
    )
    data["active_sheet"] = f"storyboard/ch{active_chapter:02d}_storyboard.csv"
    data["pointers"]["storyboard_sheet"] = data["active_sheet"]
    save_context(project_root, data)
    append_backlog(
        project_root,
        agent="system",
        action="init_project_context",
        summary=f"Initialized context for {data['project_name']}",
    )
    return data


def append_backlog(
    project_root: Path,
    *,
    agent: str,
    action: str,
    summary: str,
    chapter: int | None = None,
    scene_id: str = "",
    artifacts: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append-only event log — every agent writes here after meaningful work."""
    path = backlog_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": _now(),
        "agent": agent,
        "action": action,
        "summary": summary,
        "chapter": chapter,
        "scene_id": scene_id,
        "artifacts": artifacts or [],
        **(extra or {}),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_backlog(project_root: Path, *, limit: int = 30) -> list[dict[str, Any]]:
    path = backlog_path(project_root)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def update_context(
    project_root: Path,
    *,
    agent: str,
    phase: str | None = None,
    active_chapter: int | None = None,
    next_actions: list[str] | None = None,
    blockers: list[str] | None = None,
    summary: str = "",
    append_log: bool = True,
) -> dict[str, Any]:
    data = load_context(project_root)
    if phase:
        if phase not in DEFAULT_PHASES:
            data["phase"] = phase  # allow custom phases
        else:
            data["phase"] = phase
    if active_chapter is not None:
        data["active_chapter"] = active_chapter
        data["active_sheet"] = f"storyboard/ch{active_chapter:02d}_storyboard.csv"
        data["pointers"]["storyboard_sheet"] = data["active_sheet"]
    if next_actions is not None:
        data["next_actions"] = next_actions
    if blockers is not None:
        data["blockers"] = blockers
    agents = data.setdefault("agents", {})
    slot = agents.setdefault(agent, {})
    slot["last_seen"] = _now()
    if summary:
        slot["last_summary"] = summary
    save_context(project_root, data)
    if append_log and summary:
        append_backlog(
            project_root,
            agent=agent,
            action="update_context",
            summary=summary,
            chapter=data.get("active_chapter"),
        )
    return data


def build_agent_briefing(project_root: Path, *, backlog_limit: int = 20) -> dict[str, Any]:
    """Single payload for get_project_context — read at every agent session start."""
    ctx = load_context(project_root)
    backlog = read_backlog(project_root, limit=backlog_limit)
    sheet = project_root / (ctx.get("active_sheet") or "")
    sheet_exists = sheet.is_file()

    return {
        "context": ctx,
        "recent_backlog": backlog,
        "active_sheet_exists": sheet_exists,
        "active_sheet_path": str(sheet) if sheet_exists else str(sheet),
        "instructions_for_agents": [
            "Read this at session start before changing the project.",
            "After meaningful work: call update_project_context or append_project_log.",
            "Do not store truth only in chat — update sheet + backlog.",
            "Storyboard rows live in active_sheet CSV; this file is coordination only.",
        ],
    }

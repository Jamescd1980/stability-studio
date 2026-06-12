"""Storyboard manifest load/save, validation, and success criteria."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_VERSION = 1
DEFAULT_MANIFEST_NAME = "storyboard_manifest.json"


def manifest_path(project_root: Path, name: str = DEFAULT_MANIFEST_NAME) -> Path:
    return project_root / "logs" / name


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("manifest_version") != MANIFEST_VERSION:
        raise ValueError(f"Unsupported manifest_version (expected {MANIFEST_VERSION})")
    return data


def save_manifest(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["manifest_version"] = MANIFEST_VERSION
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def beat_file_status(project_root: Path, rel_path: str) -> dict[str, Any]:
    """Check a project-relative file; return exists + absolute path."""
    p = Path(rel_path)
    if not p.is_absolute():
        p = project_root / rel_path
    return {"path": rel_path, "absolute": str(p), "exists": p.is_file()}


def validate_manifest(
    project_root: Path,
    data: dict[str, Any],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """Evaluate success criteria. strict=True → missing required files are errors."""
    criteria = data.get("success_criteria") or {}
    required_clips = list(criteria.get("required_clips") or [])
    splice_cfg = data.get("splice") or {}
    splice_clips = list(splice_cfg.get("clips") or [])

    # Union clip paths from beats if not listed explicitly
    for beat in data.get("beats") or []:
        clip = beat.get("clip")
        if clip and clip not in required_clips:
            required_clips.append(clip)

    clip_checks = [beat_file_status(project_root, c) for c in required_clips]
    missing_clips = [c["path"] for c in clip_checks if not c["exists"]]

    splice_checks = [beat_file_status(project_root, c) for c in splice_clips]
    missing_splice = [c["path"] for c in splice_checks if not c["exists"]]

    final_rel = criteria.get("final_deliverable") or splice_cfg.get("output") or ""
    final_check = beat_file_status(project_root, final_rel) if final_rel else None

    beat_rows: list[dict[str, Any]] = []
    for beat in data.get("beats") or []:
        row: dict[str, Any] = {
            "index": beat.get("index"),
            "id": beat.get("id"),
            "status": beat.get("status", "pending"),
        }
        for key in ("clip", "audio", "chain_frame_out", "log"):
            rel = beat.get(key)
            if rel:
                row[key] = beat_file_status(project_root, rel)
        if beat.get("clip"):
            row["clip_ready"] = row.get("clip", {}).get("exists", False)
        beat_rows.append(row)

    min_beats = int(criteria.get("min_beats_complete") or len(data.get("beats") or []))
    beats_complete = sum(1 for b in beat_rows if b.get("clip_ready"))
    beats_ok = beats_complete >= min_beats

    ready = (
        not missing_clips
        and (not splice_clips or not missing_splice)
        and beats_ok
        and (not final_rel or (final_check and final_check["exists"]))
    )

    warnings: list[str] = []
    errors: list[str] = []
    for path in missing_clips:
        msg = f"Missing clip: {path}"
        (errors if strict else warnings).append(msg)
    for path in missing_splice:
        msg = f"Missing splice input: {path}"
        (errors if strict else warnings).append(msg)
    if not beats_ok:
        msg = f"Beats complete {beats_complete}/{min_beats}"
        (errors if strict else warnings).append(msg)
    if final_rel and final_check and not final_check["exists"]:
        msg = f"Final deliverable missing: {final_rel}"
        (errors if strict else warnings).append(msg)

    return {
        "ready": ready and not errors,
        "project_root": str(project_root),
        "title": data.get("title"),
        "beats_complete": beats_complete,
        "min_beats_complete": min_beats,
        "clip_checks": clip_checks,
        "missing_clips": missing_clips,
        "splice_checks": splice_checks,
        "missing_splice_inputs": missing_splice,
        "final_deliverable": final_check,
        "beats": beat_rows,
        "warnings": warnings,
        "errors": errors,
    }


def manifest_from_plan(
    *,
    title: str,
    project_root: Path,
    parsed_beats: list[dict[str, str]],
    plan: dict[str, Any],
    clip_name_template: str = "clips/beat_{index:02d}_{id}.mp4",
) -> dict[str, Any]:
    """Build a manifest skeleton from plan_storyboard_scene output."""
    beats: list[dict[str, Any]] = []
    for i, beat in enumerate(parsed_beats):
        raw_id = beat.get("id") or beat.get("action", f"beat{i + 1}")
        beat_id = "".join(c if c.isalnum() else "_" for c in raw_id.split()[0:3]).strip("_") or f"beat{i + 1}"
        beats.append(
            {
                "index": i,
                "id": beat_id,
                "action": beat.get("action", ""),
                "dialogue": beat.get("dialogue", ""),
                "clip": clip_name_template.format(index=i + 1, id=beat_id),
                "chain_frame_out": f"images/chain/beat{i}_last_frame.png",
                "audio": f"audio/beat{i + 1}_dialogue.mp3" if beat.get("dialogue") else "",
                "status": "pending",
                "log": f"logs/beat{i + 1}_{beat_id}.json",
            }
        )

    clip_paths = [b["clip"] for b in beats]
    return {
        "manifest_version": MANIFEST_VERSION,
        "title": title,
        "status": "planned",
        "project_root": str(project_root),
        "fps": plan.get("frame_rate") or 16.0,
        "success_criteria": {
            "required_clips": clip_paths,
            "min_beats_complete": len(beats),
            "final_deliverable": "final/storyboard_spliced.mp4",
        },
        "splice": {
            "tail_drop": 1,
            "skip_head": 1,
            "clips": clip_paths,
            "output": "final/storyboard_spliced.mp4",
        },
        "beats": beats,
        "plan": {
            "hero_steps": plan.get("hero_steps"),
            "post_steps": plan.get("post_steps"),
            "gpu_order_16gb": plan.get("gpu_order_16gb"),
        },
    }

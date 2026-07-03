"""Spreadsheet-driven VN storyboard — CSV source of truth, asset naming, Ren'Py skeleton."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHEET_VERSION = 1
SHEET_DIR = "storyboard"

# Human-editable in Excel / Google Sheets / LibreOffice Calc.
SHEET_COLUMNS: tuple[str, ...] = (
    "scene_id",
    "chapter",
    "sequence",
    "type",
    "location",
    "characters",
    "action",
    "dialogue",
    "speaker",
    "image_asset",
    "video_asset",
    "audio_asset",
    "style",
    "prompt_positive",
    "prompt_negative",
    "status",
    "notes",
)

SHEET_TYPES: frozenset[str] = frozenset(
    {
        "still",  # VN panel / key illustration
        "background",  # scene BG only
        "sprite",  # character on BG
        "dialogue",  # line with optional sprite
        "narration",  # narrator box, no sprite required
        "video",  # hero/draft clip beat
        "sfx",  # sound effect cue
        "music",  # music cue
        "choice",  # branch placeholder
        "transition",  # fade, cut, chapter break
    }
)

STATUS_VALUES: frozenset[str] = frozenset(
    {"planned", "prompt_ready", "generating", "review", "approved", "rejected", "skip"}
)


def sheet_path(project_root: Path, chapter: int | str) -> Path:
    ch = int(chapter)
    return project_root / SHEET_DIR / f"ch{ch:02d}_storyboard.csv"


def _slug(text: str, max_len: int = 32) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return (s[:max_len] or "scene").rstrip("_")


def suggest_scene_id(chapter: int, sequence: int, row_type: str, action: str = "") -> str:
    return f"ch{chapter:02d}_{sequence:03d}_{row_type}_{_slug(action, 24)}"


def default_image_asset(scene_id: str) -> str:
    return f"images/{scene_id}.png"


def default_video_asset(scene_id: str) -> str:
    return f"clips/{scene_id}.mp4"


def default_audio_asset(scene_id: str, speaker: str = "") -> str:
    slug = _slug(speaker or "line", 16)
    return f"audio/{scene_id}_{slug}.mp3"


def init_chapter_sheet(
    project_root: Path,
    *,
    chapter: int,
    title: str = "",
    seed_rows: list[dict[str, str]] | None = None,
) -> Path:
    """Create storyboard/ + empty or seeded CSV for a chapter."""
    (project_root / SHEET_DIR).mkdir(parents=True, exist_ok=True)
    path = sheet_path(project_root, chapter)
    if path.is_file():
        return path

    rows: list[dict[str, str]] = []
    if seed_rows:
        rows = seed_rows
    else:
        rows = [
            _blank_row(
                chapter=chapter,
                sequence=1,
                row_type="narration",
                action="Opening narration or scene-setter",
                dialogue="",
            ),
            _blank_row(
                chapter=chapter,
                sequence=2,
                row_type="still",
                action="Establishing shot — describe composition",
                dialogue="",
            ),
            _blank_row(
                chapter=chapter,
                sequence=3,
                row_type="dialogue",
                action="Character visible — pose and emotion",
                dialogue="First spoken line.",
                speaker="character_name",
            ),
        ]

    save_sheet(path, rows, meta={"title": title or f"Chapter {chapter}", "chapter": chapter})
    return path


def _blank_row(
    *,
    chapter: int,
    sequence: int,
    row_type: str,
    action: str,
    dialogue: str = "",
    speaker: str = "",
) -> dict[str, str]:
    scene_id = suggest_scene_id(chapter, sequence, row_type, action)
    row = {col: "" for col in SHEET_COLUMNS}
    row.update(
        {
            "scene_id": scene_id,
            "chapter": str(chapter),
            "sequence": str(sequence),
            "type": row_type,
            "action": action,
            "dialogue": dialogue,
            "speaker": speaker,
            "image_asset": default_image_asset(scene_id)
            if row_type in {"still", "background", "sprite", "dialogue"}
            else "",
            "video_asset": default_video_asset(scene_id) if row_type == "video" else "",
            "audio_asset": default_audio_asset(scene_id, speaker)
            if dialogue and row_type in {"dialogue", "narration"}
            else "",
            "style": "ilustmix" if row_type in {"still", "sprite", "background"} else "",
            "status": "planned",
        }
    )
    return row


def load_sheet(path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Storyboard sheet not found: {path}")
    meta: dict[str, Any] = {}
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Empty CSV: {path}")
        for raw in reader:
            if not any((v or "").strip() for v in raw.values()):
                continue
            if raw.get("scene_id", "").startswith("#"):
                continue
            row = {col: (raw.get(col) or "").strip() for col in SHEET_COLUMNS}
            if not row["scene_id"]:
                ch = int(row.get("chapter") or 1)
                seq = int(row.get("sequence") or len(rows) + 1)
                row["scene_id"] = suggest_scene_id(ch, seq, row.get("type") or "still", row.get("action", ""))
            rows.append(row)
    sidecar = path.with_suffix(".json")
    if sidecar.is_file():
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
    return rows, meta


def save_sheet(path: Path, rows: list[dict[str, str]], *, meta: dict[str, Any] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(SHEET_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in SHEET_COLUMNS})
    sidecar = path.with_suffix(".json")
    payload = {
        "sheet_version": SHEET_VERSION,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **(meta or {}),
        "row_count": len(rows),
    }
    sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def validate_sheet(project_root: Path, path: Path, *, strict: bool = False) -> dict[str, Any]:
    rows, meta = load_sheet(path)
    issues: list[str] = []
    warnings: list[str] = []
    checked: list[dict[str, Any]] = []

    seen_ids: set[str] = set()
    for row in rows:
        sid = row["scene_id"]
        if sid in seen_ids:
            issues.append(f"Duplicate scene_id: {sid}")
        seen_ids.add(sid)

        rtype = row.get("type") or "still"
        if rtype not in SHEET_TYPES:
            warnings.append(f"{sid}: unknown type '{rtype}'")

        status = row.get("status") or "planned"
        if status not in STATUS_VALUES:
            warnings.append(f"{sid}: unknown status '{status}'")

        row_report: dict[str, Any] = {
            "scene_id": sid,
            "sequence": row.get("sequence"),
            "type": rtype,
            "status": status,
        }

        for asset_key, label in (
            ("image_asset", "image"),
            ("video_asset", "video"),
            ("audio_asset", "audio"),
        ):
            rel = row.get(asset_key, "")
            if not rel:
                continue
            full = project_root / rel.replace("\\", "/")
            exists = full.is_file()
            row_report[label] = {"path": rel, "exists": exists}
            if status == "approved" and not exists:
                msg = f"{sid}: approved but missing {label}: {rel}"
                (issues if strict else warnings).append(msg)

        if rtype in {"still", "sprite", "background", "dialogue"} and not row.get("image_asset"):
            warnings.append(f"{sid}: {rtype} row has no image_asset path")
        if rtype == "video" and not row.get("video_asset"):
            warnings.append(f"{sid}: video row has no video_asset path")
        if row.get("dialogue") and not row.get("audio_asset") and rtype in {"dialogue", "narration"}:
            warnings.append(f"{sid}: dialogue without audio_asset (MOSS target)")

        checked.append(row_report)

    image_ready = sum(1 for r in checked if (r.get("image") or {}).get("exists"))
    video_ready = sum(1 for r in checked if (r.get("video") or {}).get("exists"))
    audio_ready = sum(1 for r in checked if (r.get("audio") or {}).get("exists"))

    return {
        "ready": not issues,
        "sheet": str(path),
        "project_root": str(project_root),
        "meta": meta,
        "row_count": len(rows),
        "assets": {
            "images_on_disk": image_ready,
            "videos_on_disk": video_ready,
            "audio_on_disk": audio_ready,
        },
        "rows": checked,
        "warnings": warnings,
        "errors": issues,
    }


def rows_needing_generation(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Rows where status is prompt_ready or planned with prompts filled."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") in {"approved", "skip", "rejected"}:
            continue
        rtype = row.get("type", "")
        if rtype in {"still", "background", "sprite", "dialogue"} and row.get("prompt_positive"):
            out.append(
                {
                    "scene_id": row["scene_id"],
                    "tool": "generate_image",
                    "style": row.get("style") or "ilustmix",
                    "prompt": row["prompt_positive"],
                    "negative_prompt": row.get("prompt_negative", ""),
                    "target": row.get("image_asset") or default_image_asset(row["scene_id"]),
                }
            )
        elif rtype == "video" and row.get("action"):
            out.append(
                {
                    "scene_id": row["scene_id"],
                    "tool": "generate_video_hero",
                    "prompt": row.get("prompt_positive") or row["action"],
                    "target": row.get("video_asset") or default_video_asset(row["scene_id"]),
                }
            )
        elif row.get("dialogue") and row.get("audio_asset"):
            out.append(
                {
                    "scene_id": row["scene_id"],
                    "tool": "generate_audio",
                    "mode": "voice_design",
                    "text": row["dialogue"],
                    "speaker": row.get("speaker", ""),
                    "target": row["audio_asset"],
                }
            )
    return out


def export_renpy_skeleton(
    project_root: Path,
    path: Path,
    *,
    chapter: int | None = None,
    game_name: str = "vn_game",
) -> dict[str, Any]:
    """Emit Ren'Py label skeleton under renpy/generated/ (human review required)."""
    rows, meta = load_sheet(path)
    if chapter is not None:
        rows = [r for r in rows if int(r.get("chapter") or 0) == chapter]
    if not rows:
        raise ValueError("No rows to export")

    ch = chapter or int(rows[0].get("chapter") or 1)
    out_dir = project_root / "renpy" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    script_path = out_dir / f"ch{ch:02d}_script.rpy"
    defs_path = out_dir / f"ch{ch:02d}_images.rpy"

    image_defs: list[str] = []
    script_lines: list[str] = [
        f"# AUTO-GENERATED skeleton — review before shipping",
        f"# Source: {path.name}",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"label ch{ch:02d}_start:",
    ]

    for row in sorted(rows, key=lambda r: int(r.get("sequence") or 0)):
        sid = row["scene_id"]
        rtype = row.get("type", "still")
        script_lines.append(f"    # [{sid}] {rtype}: {row.get('action', '')[:80]}")

        img = row.get("image_asset", "")
        if img and rtype in {"still", "background", "sprite", "dialogue"}:
            ren_img = Path(img).stem
            image_defs.append(f"image {ren_img} = \"../{img.replace(chr(92), '/')}\"")
            if rtype == "background":
                script_lines.append(f"    scene {ren_img}")
            elif rtype in {"sprite", "dialogue", "still"}:
                script_lines.append(f"    show {ren_img}")

        if row.get("dialogue"):
            speaker = (row.get("speaker") or "").strip()
            line = row["dialogue"].replace('"', '\\"')
            if speaker:
                script_lines.append(f"    {speaker} \"{line}\"")
            else:
                script_lines.append(f"    \"{line}\"")

        aud = row.get("audio_asset", "")
        if aud:
            script_lines.append(f"    # play audio: {aud}")

        vid = row.get("video_asset", "")
        if vid and rtype == "video":
            script_lines.append(f"    # TODO: movie cutscene — {vid}")

        if rtype == "choice":
            script_lines.append("    menu:")
            script_lines.append("        \"Branch A (edit in sheet)\":")
            script_lines.append("            pass")
            script_lines.append("        \"Branch B (edit in sheet)\":")
            script_lines.append("            pass")

        if rtype == "transition":
            script_lines.append("    with dissolve")

        script_lines.append("")

    script_lines.append(f"    return  # end ch{ch:02d}")
    defs_path.write_text("\n".join(sorted(set(image_defs))) + "\n", encoding="utf-8")
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")

    return {
        "chapter": ch,
        "game_name": game_name,
        "script": str(script_path),
        "image_definitions": str(defs_path),
        "row_count": len(rows),
        "note": "Copy into Ren'Py project after review; paths are relative to generated folder.",
    }

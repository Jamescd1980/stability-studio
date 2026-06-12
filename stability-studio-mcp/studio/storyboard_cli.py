"""Reusable storyboard CLI module — paths, manifest I/O, splice, plan/check/splice runners."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from studio.config import load_config
from studio.project_layout import DEFAULT_SUBDIRS, layout_subdirs, project_paths
from studio.storyboard import plan_storyboard_scene
from studio.storyboard_manifest import (
    load_manifest,
    manifest_from_plan,
    manifest_path,
    save_manifest,
    validate_manifest,
)


def resolve_project_dir(
    project_dir: str | Path | None = None,
    *,
    cfg: dict[str, Any] | None = None,
    create: bool = True,
) -> Path:
    """Project root: explicit path > config outputs.delivery."""
    if project_dir:
        root = Path(project_dir).expanduser().resolve()
    else:
        cfg = cfg or load_config()
        raw = (cfg.get("outputs") or {}).get("delivery")
        if not raw:
            raise ValueError(
                "No project directory. Pass --project-dir or set outputs.delivery in config.yaml"
            )
        root = Path(raw).expanduser().resolve()

    if create:
        for rel in DEFAULT_SUBDIRS:
            (root / rel).mkdir(parents=True, exist_ok=True)
    return root


def paths_for_project(project_dir: Path, cfg: dict[str, Any] | None = None) -> dict[str, Path]:
    cfg = cfg or load_config()
    subs = layout_subdirs(cfg)
    return {key: project_dir / rel for key, rel in subs.items()}


def storyboard_arg_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument(
        "--project-dir",
        default="",
        help="Delivery project root (default: outputs.delivery from config.yaml)",
    )
    p.add_argument(
        "--manifest",
        default="storyboard_manifest.json",
        help="Manifest filename under project logs/",
    )
    return p


def ffmpeg_bin(cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or {}
    comfy = Path((cfg.get("stability_matrix", {}).get("packages") or {}).get("comfyui", ""))
    bundled = (
        comfy
        / "venv"
        / "Lib"
        / "site-packages"
        / "imageio_ffmpeg"
        / "binaries"
        / "ffmpeg-win-x86_64-v7.1.exe"
    )
    if bundled.is_file():
        return str(bundled)
    return "ffmpeg"


def splice_from_manifest(
    project_root: Path,
    manifest: dict[str, Any],
    *,
    manifest_file: str = "storyboard_manifest.json",
    cfg: dict[str, Any] | None = None,
    skip_missing: bool = False,
) -> dict[str, Any]:
    """Join manifest splice.clips with tail_drop / skip_head frame logic."""
    splice_cfg = manifest.get("splice") or {}
    clip_rels = list(splice_cfg.get("clips") or [])
    if len(clip_rels) < 2:
        raise ValueError("splice.clips must list at least two project-relative MP4 paths")

    fps = int(manifest.get("fps") or 16)
    tail_drop = int(splice_cfg.get("tail_drop", 1))
    skip_head = int(splice_cfg.get("skip_head", 1))
    out_rel = splice_cfg.get("output") or "final/storyboard_spliced.mp4"
    out_path = project_root / out_rel

    skipped: list[str] = []
    available: list[str] = []
    for rel in clip_rels:
        if (project_root / rel).is_file():
            available.append(rel)
        elif skip_missing:
            skipped.append(rel)
        else:
            raise FileNotFoundError(f"Missing clip for splice: {rel}")

    clips = [project_root / r for r in available]
    if len(clips) < 2:
        raise FileNotFoundError(
            f"Need at least 2 clips after skip; missing={skipped or 'see manifest'}"
        )

    from studio.video_utils import probe_video

    frame_counts = [int(probe_video(p).get("frame_count") or 49) for p in clips]

    parts: list[str] = []
    labels: list[str] = []
    for i, n in enumerate(frame_counts):
        if i == 0:
            end = n - tail_drop - 1
            parts.append(f"[{i}:v]select='lte(n\\,{end})',setpts=N/{fps}/TB[v{i}]")
        elif i < len(frame_counts) - 1:
            start, end = skip_head, n - tail_drop - 1
            parts.append(
                f"[{i}:v]select='between(n\\,{start}\\,{end})',setpts=N/{fps}/TB[v{i}]"
            )
        else:
            start, end = skip_head, n - 1
            parts.append(
                f"[{i}:v]select='between(n\\,{start}\\,{end})',setpts=N/{fps}/TB[v{i}]"
            )
        labels.append(f"[v{i}]")

    n_clips = len(clips)
    filter_complex = ";".join(parts) + f";{''.join(labels)}concat=n={n_clips}:v=1:a=0[outv]"

    cmd = ["-y"]
    for p in clips:
        cmd.extend(["-i", str(p)])
    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            str(out_path),
        ]
    )

    subprocess.run([ffmpeg_bin(cfg), *cmd], check=True, capture_output=True)
    out_info = probe_video(out_path)

    payload: dict[str, Any] = {
        "status": "success",
        "inputs": [str(p) for p in clips],
        "skipped": skipped,
        "output": str(out_path),
        "output_rel": out_rel,
        "duration_sec": out_info.get("duration_sec"),
        "fps": fps,
        "tail_drop": tail_drop,
        "skip_head": skip_head,
    }

    (project_root / "logs" / "storyboard_splice.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    manifest["status"] = "spliced"
    manifest.setdefault("success_criteria", {})["final_deliverable"] = out_rel
    save_manifest(project_root / "logs" / manifest_file, manifest)
    return payload


def run_plan(
    *,
    project_dir: str | Path | None,
    manifest_name: str,
    script: str,
    script_file: str,
    title: str,
    hero_image: str,
    food_group: str,
    voice_instruction: str,
    lipsync: bool,
    fade_last: bool,
    clip_template: str,
) -> dict[str, Any]:
    cfg = load_config()
    project_root = resolve_project_dir(project_dir or None, cfg=cfg)
    script_text = script
    if script_file:
        script_text = Path(script_file).read_text(encoding="utf-8")
    if not script_text.strip():
        raise ValueError("Provide script or script_file")

    plan = plan_storyboard_scene(
        script=script_text,
        hero_image=hero_image,
        food_group=food_group,
        voice_instruction=voice_instruction,
        project_name=title,
        include_lipsync=lipsync,
        splice_clips=True,
        fade_last_beat=fade_last,
    )
    beats = plan.get("parsed_beats") or []
    manifest = manifest_from_plan(
        title=title,
        project_root=project_root,
        parsed_beats=beats,
        plan=plan,
    )
    if clip_template:
        for i, beat in enumerate(manifest["beats"]):
            beat["clip"] = clip_template.format(index=i + 1, id=beat["id"], n=i)
        manifest["success_criteria"]["required_clips"] = [b["clip"] for b in manifest["beats"]]
        manifest["splice"]["clips"] = manifest["success_criteria"]["required_clips"]

    out = manifest_path(project_root, manifest_name)
    save_manifest(out, manifest)
    return {"status": "planned", "manifest": str(out), "beats": len(beats)}


def run_check(
    *,
    project_dir: str | Path | None,
    manifest_name: str,
    strict: bool = False,
) -> dict[str, Any]:
    cfg = load_config()
    project_root = resolve_project_dir(project_dir or None, cfg=cfg, create=False)
    mpath = manifest_path(project_root, manifest_name)
    manifest = load_manifest(mpath)
    return validate_manifest(project_root, manifest, strict=strict)


def run_splice(
    *,
    project_dir: str | Path | None,
    manifest_name: str,
    skip_missing: bool = False,
) -> tuple[int, dict[str, Any]]:
    cfg = load_config()
    project_root = resolve_project_dir(project_dir or None, cfg=cfg)
    mpath = manifest_path(project_root, manifest_name)
    manifest = load_manifest(mpath)
    check = validate_manifest(project_root, manifest, strict=False)
    if check["missing_splice_inputs"] and not skip_missing:
        return 2, {
            "status": "blocked",
            "missing": check["missing_splice_inputs"],
            "hint": "Generate missing clips or pass --skip-missing",
        }
    try:
        result = splice_from_manifest(
            project_root,
            manifest,
            manifest_file=manifest_name,
            cfg=cfg,
            skip_missing=skip_missing,
        )
        return 0, result
    except Exception as exc:
        return 1, {"status": "failed", "error": str(exc)}

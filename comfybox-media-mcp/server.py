#!/usr/bin/env python3
"""ComfyBox Media MCP — browse, view, and organize D:\\ComfyBox Images and Videos for Jan."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

ROOT = Path(os.environ.get("COMFYBOX_MEDIA_ROOT", r"D:\ComfyBox Images and Videos")).resolve()

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".jfif", ".bmp", ".gif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}

mcp = FastMCP(
    "comfybox-media",
    instructions=(
        "Browse and review media under the ComfyBox delivery folder. "
        "Use list_media to find files, then view_image / view_video_frame so you can SEE pixels "
        "(stability-studio only returns paths — it does not show images). "
        "Pass the returned absolute path into stability-studio generate_video / edit_image. "
        "Organize with copy_media / move_media / rename_media (sandboxed to the delivery root). "
        "Never invent D:\\Users\\... paths."
    ),
)


def _ensure_root() -> Path:
    if not ROOT.is_dir():
        raise FileNotFoundError(f"ComfyBox media root missing: {ROOT}")
    return ROOT


def _safe_resolve(path: str | Path) -> Path:
    """Resolve path; must stay inside ROOT (or be relative to ROOT)."""
    root = _ensure_root()
    raw = Path(path)
    candidate = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes media root: {candidate}") from exc
    return candidate


def _rel(path: Path) -> str:
    return str(path.relative_to(_ensure_root())).replace("\\", "/")


def _kind(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in IMAGE_EXTS:
        return "image"
    if suf in VIDEO_EXTS:
        return "video"
    return "other"


def _file_info(path: Path) -> dict:
    st = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "relative": _rel(path),
        "kind": _kind(path),
        "bytes": st.st_size,
        "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }


def _review_jpeg(path: Path, max_edge: int = 1280, quality: int = 85) -> bytes:
    """Downscale for vision context; keep aspect ratio."""
    with PILImage.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, max_edge / max(w, h))
        if scale < 1.0:
            im = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), PILImage.Resampling.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("ffmpeg not found on PATH")
    return found


@mcp.tool()
def media_root() -> str:
    """Return the sandboxed ComfyBox delivery root and top-level folders."""
    root = _ensure_root()
    folders = sorted(
        [
            {"name": p.name, "path": str(p), "relative": p.name}
            for p in root.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ],
        key=lambda x: x["name"].lower(),
    )
    return json.dumps(
        {
            "root": str(root),
            "folders": folders,
            "hint": "list_media(subdir='User Import') or list_media(query='bj'). view_image to SEE pixels.",
        },
        indent=2,
    )


@mcp.tool()
def list_media(
    subdir: str = "",
    query: str = "",
    kind: str = "all",
    max_files: int = 60,
    recursive: bool = True,
) -> str:
    """
    List images/videos under the ComfyBox delivery folder.

    Args:
        subdir: Relative folder (e.g. User Import, Images, Video, clips). Empty = whole root.
        query: Case-insensitive substring filter on filename.
        kind: all | image | video
        max_files: Cap results (newest first).
        recursive: Search subfolders.
    """
    root = _ensure_root()
    base = _safe_resolve(subdir) if subdir.strip() else root
    if not base.is_dir():
        return json.dumps({"error": f"Not a directory: {base}"}, indent=2)

    q = query.strip().lower()
    kind_n = (kind or "all").strip().lower()
    if kind_n not in {"all", "image", "video"}:
        return json.dumps({"error": "kind must be all|image|video"}, indent=2)

    matches: list[Path] = []
    iterator = base.rglob("*") if recursive else base.iterdir()
    for path in iterator:
        if not path.is_file():
            continue
        k = _kind(path)
        if k == "other":
            continue
        if kind_n != "all" and k != kind_n:
            continue
        if q and q not in path.name.lower():
            continue
        matches.append(path)

    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    capped = matches[: max(1, min(int(max_files), 200))]
    return json.dumps(
        {
            "root": str(root),
            "base": str(base),
            "query": query or None,
            "kind": kind_n,
            "count": len(capped),
            "truncated": len(matches) > len(capped),
            "files": [_file_info(p) for p in capped],
            "hint": "Call view_image(path=...) or view_video_frame(path=...) to review visually.",
        },
        indent=2,
    )


@mcp.tool()
def view_image(path: str, max_edge: int = 1280) -> list:
    """
    Load an image so you can SEE it (returns image bytes + path metadata).

    Args:
        path: Absolute path or path relative to the ComfyBox root.
        max_edge: Max width/height for the review preview (keeps chat context small).
    """
    src = _safe_resolve(path)
    if not src.is_file():
        return [json.dumps({"error": f"Not found: {src}"})]
    if _kind(src) != "image":
        return [json.dumps({"error": f"Not an image: {src}", "hint": "Use view_video_frame for videos."})]

    meta = {
        **_file_info(src),
        "review_max_edge": max_edge,
        "use_with": "Pass path into stability-studio generate_video / edit_image exactly.",
    }
    preview = _review_jpeg(src, max_edge=max(256, min(int(max_edge), 2048)))
    return [json.dumps(meta, indent=2), Image(data=preview, format="jpeg")]


@mcp.tool()
def view_video_frame(path: str, time_seconds: float = 0.5, max_edge: int = 1280) -> list:
    """
    Extract one frame from a video so you can SEE it (ffmpeg + preview image).

    Args:
        path: Absolute or root-relative video path.
        time_seconds: Timestamp to grab (default 0.5s).
        max_edge: Max edge for the review preview.
    """
    src = _safe_resolve(path)
    if not src.is_file():
        return [json.dumps({"error": f"Not found: {src}"})]
    if _kind(src) != "video":
        return [json.dumps({"error": f"Not a video: {src}", "hint": "Use view_image for stills."})]

    tmp = _ensure_root() / "temp" / "_mcp_frame_preview.jpg"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg(),
        "-y",
        "-ss",
        str(max(0.0, float(time_seconds))),
        "-i",
        str(src),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    except subprocess.CalledProcessError as exc:
        return [json.dumps({"error": "ffmpeg failed", "stderr": (exc.stderr or "")[-800]}, indent=2)]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [json.dumps({"error": str(exc)}, indent=2)]

    meta = {
        **_file_info(src),
        "frame_time_seconds": time_seconds,
        "frame_preview_path": str(tmp),
        "use_with": "Pass path into stability-studio tools; this preview is for review only.",
    }
    preview = _review_jpeg(tmp, max_edge=max(256, min(int(max_edge), 2048)))
    return [json.dumps(meta, indent=2), Image(data=preview, format="jpeg")]


@mcp.tool()
def copy_media(src: str, dest_relative: str, overwrite: bool = False) -> str:
    """
    Copy a file inside the ComfyBox root (e.g. User Import/foo.png → source/foo.png).

    Args:
        src: Source absolute or relative path.
        dest_relative: Destination path relative to root (file path, not just folder).
        overwrite: Replace existing destination.
    """
    source = _safe_resolve(src)
    dest = _safe_resolve(dest_relative)
    if not source.is_file():
        return json.dumps({"ok": False, "error": f"Source missing: {source}"}, indent=2)
    if dest.exists() and not overwrite:
        return json.dumps({"ok": False, "error": f"Destination exists: {dest}"}, indent=2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return json.dumps({"ok": True, "copied": _file_info(dest)}, indent=2)


@mcp.tool()
def move_media(src: str, dest_relative: str, overwrite: bool = False) -> str:
    """Move/rename a file inside the ComfyBox root (does not delete outside the sandbox)."""
    source = _safe_resolve(src)
    dest = _safe_resolve(dest_relative)
    if not source.is_file():
        return json.dumps({"ok": False, "error": f"Source missing: {source}"}, indent=2)
    if dest.exists() and not overwrite:
        return json.dumps({"ok": False, "error": f"Destination exists: {dest}"}, indent=2)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return json.dumps({"ok": True, "moved": _file_info(dest)}, indent=2)


@mcp.tool()
def rename_media(src: str, new_name: str, overwrite: bool = False) -> str:
    """Rename a file in place (same folder). new_name is filename only, no path separators."""
    source = _safe_resolve(src)
    name = Path(new_name).name
    if not name or name != new_name or "/" in new_name or "\\" in new_name:
        return json.dumps({"ok": False, "error": "new_name must be a plain filename"}, indent=2)
    return move_media(str(source), str(source.parent.relative_to(_ensure_root()) / name), overwrite=overwrite)


@mcp.tool()
def open_in_explorer(path: str = "") -> str:
    """Reveal a file or folder in Windows Explorer (defaults to media root)."""
    target = _safe_resolve(path) if path.strip() else _ensure_root()
    if target.is_file():
        subprocess.Popen(["explorer", "/select,", str(target)])
    else:
        subprocess.Popen(["explorer", str(target)])
    return json.dumps({"ok": True, "opened": str(target)}, indent=2)


if __name__ == "__main__":
    mcp.run()

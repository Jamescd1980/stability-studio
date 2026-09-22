"""Browse / view / organize the GenerationHost delivery folder (and Desktop New Images for review)."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image as PILImage

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".jfif", ".bmp", ".gif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}


def delivery_root(cfg: dict[str, Any]) -> Path:
    from studio.output_paths import delivery_dir

    root = delivery_dir(cfg)
    if root is None:
        raise FileNotFoundError("outputs.delivery not set in config.yaml")
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Delivery folder missing: {root}")
    return root


def allowed_roots(cfg: dict[str, Any]) -> list[Path]:
    roots = [delivery_root(cfg)]
    desktop = Path.home() / "Desktop" / "New Images"
    if desktop.is_dir():
        roots.append(desktop.resolve())
    return roots


def _safe_resolve(cfg: dict[str, Any], path: str | Path) -> Path:
    raw = Path(path)
    if not raw.is_absolute():
        candidate = (delivery_root(cfg) / raw).resolve()
    else:
        candidate = raw.resolve()
    for root in allowed_roots(cfg):
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise ValueError(
        f"Path not under delivery or Desktop\\New Images: {candidate}"
    )


def _kind(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in IMAGE_EXTS:
        return "image"
    if suf in VIDEO_EXTS:
        return "video"
    return "other"


def _file_info(cfg: dict[str, Any], path: Path) -> dict[str, Any]:
    st = path.stat()
    try:
        rel = str(path.relative_to(delivery_root(cfg))).replace("\\", "/")
    except ValueError:
        rel = str(path)
    return {
        "name": path.name,
        "path": str(path),
        "relative": rel,
        "kind": _kind(path),
        "bytes": st.st_size,
        "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }


def _review_jpeg(path: Path, max_edge: int = 1280, quality: int = 85) -> bytes:
    with PILImage.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, max_edge / max(w, h))
        if scale < 1.0:
            im = im.resize(
                (max(1, int(w * scale)), max(1, int(h * scale))),
                PILImage.Resampling.LANCZOS,
            )
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("ffmpeg not found on PATH")
    return found


def media_root_info(cfg: dict[str, Any]) -> dict[str, Any]:
    root = delivery_root(cfg)
    folders = sorted(
        [
            {"name": p.name, "path": str(p), "relative": p.name}
            for p in root.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ],
        key=lambda x: x["name"].lower(),
    )
    return {
        "root": str(root),
        "also_allowed": [str(p) for p in allowed_roots(cfg) if p != root],
        "folders": folders,
        "hint": (
            "list_delivery_media(subdir='User Import') then view_delivery_image(path=...) "
            "to SEE pixels. Pass path into generate_video / edit_image."
        ),
    }


def list_delivery_media(
    cfg: dict[str, Any],
    subdir: str = "",
    query: str = "",
    kind: str = "all",
    max_files: int = 60,
    recursive: bool = True,
) -> dict[str, Any]:
    root = delivery_root(cfg)
    base = _safe_resolve(cfg, subdir) if subdir.strip() else root
    if not base.is_dir():
        return {"error": f"Not a directory: {base}"}

    q = query.strip().lower()
    kind_n = (kind or "all").strip().lower()
    if kind_n not in {"all", "image", "video"}:
        return {"error": "kind must be all|image|video"}

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
    return {
        "root": str(root),
        "base": str(base),
        "query": query or None,
        "kind": kind_n,
        "count": len(capped),
        "truncated": len(matches) > len(capped),
        "files": [_file_info(cfg, p) for p in capped],
        "hint": "Call view_delivery_image or view_delivery_video_frame to review visually.",
    }


def view_delivery_image_payload(
    cfg: dict[str, Any],
    path: str,
    max_edge: int = 1280,
) -> tuple[dict[str, Any], bytes | None]:
    src = _safe_resolve(cfg, path)
    if not src.is_file():
        return {"error": f"Not found: {src}"}, None
    if _kind(src) != "image":
        return {
            "error": f"Not an image: {src}",
            "hint": "Use view_delivery_video_frame for videos.",
        }, None
    meta = {
        **_file_info(cfg, src),
        "review_max_edge": max_edge,
        "use_with": "Pass path into generate_video / edit_image exactly.",
    }
    preview = _review_jpeg(src, max_edge=max(256, min(int(max_edge), 2048)))
    return meta, preview


def view_delivery_video_frame_payload(
    cfg: dict[str, Any],
    path: str,
    time_seconds: float = 0.5,
    max_edge: int = 1280,
) -> tuple[dict[str, Any], bytes | None]:
    src = _safe_resolve(cfg, path)
    if not src.is_file():
        return {"error": f"Not found: {src}"}, None
    if _kind(src) != "video":
        return {
            "error": f"Not a video: {src}",
            "hint": "Use view_delivery_image for stills.",
        }, None

    tmp = delivery_root(cfg) / "temp" / "_mcp_frame_preview.jpg"
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
        return {"error": "ffmpeg failed", "stderr": (exc.stderr or "")[-800]}, None
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}, None

    meta = {
        **_file_info(cfg, src),
        "frame_time_seconds": time_seconds,
        "frame_preview_path": str(tmp),
        "use_with": "Pass path into generate tools; this preview is for review only.",
    }
    preview = _review_jpeg(tmp, max_edge=max(256, min(int(max_edge), 2048)))
    return meta, preview


def copy_delivery_media(
    cfg: dict[str, Any],
    src: str,
    dest_relative: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = _safe_resolve(cfg, src)
    dest = _safe_resolve(cfg, dest_relative)
    # Writes only under delivery root
    try:
        dest.relative_to(delivery_root(cfg))
    except ValueError:
        return {"ok": False, "error": "Destination must be inside delivery folder"}
    if not source.is_file():
        return {"ok": False, "error": f"Source missing: {source}"}
    if dest.exists() and not overwrite:
        return {"ok": False, "error": f"Destination exists: {dest}"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return {"ok": True, "copied": _file_info(cfg, dest)}


def move_delivery_media(
    cfg: dict[str, Any],
    src: str,
    dest_relative: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = _safe_resolve(cfg, src)
    dest = _safe_resolve(cfg, dest_relative)
    root = delivery_root(cfg)
    try:
        source.relative_to(root)
        dest.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "move_media only inside delivery folder"}
    if not source.is_file():
        return {"ok": False, "error": f"Source missing: {source}"}
    if dest.exists() and not overwrite:
        return {"ok": False, "error": f"Destination exists: {dest}"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return {"ok": True, "moved": _file_info(cfg, dest)}


def rename_delivery_media(
    cfg: dict[str, Any],
    src: str,
    new_name: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = _safe_resolve(cfg, src)
    name = Path(new_name).name
    if not name or name != new_name or "/" in new_name or "\\" in new_name:
        return {"ok": False, "error": "new_name must be a plain filename"}
    rel = source.parent.relative_to(delivery_root(cfg)) / name
    return move_delivery_media(cfg, str(source), str(rel), overwrite=overwrite)


def open_delivery_in_explorer(cfg: dict[str, Any], path: str = "") -> dict[str, Any]:
    target = _safe_resolve(cfg, path) if path.strip() else delivery_root(cfg)
    if target.is_file():
        subprocess.Popen(["explorer", "/select,", str(target)])
    else:
        subprocess.Popen(["explorer", str(target)])
    return {"ok": True, "opened": str(target)}


def recycle_delivery_media(cfg: dict[str, Any], path: str) -> dict[str, Any]:
    """Send a delivery (or Desktop\\New Images) file/folder to the Recycle Bin.

    Never hard-deletes. Paths outside the sandbox are refused.
    """
    import sys

    target = _safe_resolve(cfg, path)
    if not target.exists():
        return {"ok": False, "error": f"Missing: {target}"}
    info = (
        _file_info(cfg, target)
        if target.is_file()
        else {"name": target.name, "path": str(target), "kind": "dir"}
    )
    scripts = Path(__file__).resolve().parents[1] / "scripts" / "general"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from recycle_path import recycle  # type: ignore

    if not recycle(target):
        return {"ok": False, "error": f"Recycle Bin failed for {target}", "target": info}
    return {
        "ok": True,
        "recycled": info,
        "note": "Sent to Recycle Bin (not permanent delete)",
    }

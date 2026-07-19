#!/usr/bin/env python3
"""Orla action sidecar — gallery open/display + phonetic rewrite for Myra ask_orla.

Listens on 0.0.0.0:11436 (JSON). Ollama Orla chat stays on :11434.

Gallery vocabulary (spoken → action):
  last image     = last one *displayed* (viewing history), not newest by date
  newest image   = newest by file mtime under ComfyBox Images/Video
  next / previous = walk the current batch in creation order
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = os.environ.get("ORLA_TOOLS_HOST", "0.0.0.0")
PORT = int(os.environ.get("ORLA_TOOLS_PORT", "11436"))
OLLAMA = os.environ.get("ORLA_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
ORLA_MODEL = os.environ.get("ORLA_MODEL", "orla")
PHONETIC_OUT = Path(os.environ.get("ORLA_PHONETIC_DIR", r"D:\studio-agent\orla-phonetic"))
KOKORO_URL = os.environ.get("ORLA_KOKORO_URL", "http://127.0.0.1:8090").rstrip("/")
COMFYBOX = Path(os.environ.get("ORLA_COMFYBOX", r"D:\ComfyBox Images and Videos"))
IMAGES_DIR = Path(os.environ.get("ORLA_IMAGES_DIR", str(COMFYBOX / "Images")))
VIDEO_DIR = Path(os.environ.get("ORLA_VIDEO_DIR", str(COMFYBOX / "Video")))
STATE_PATH = Path(
    os.environ.get("ORLA_GALLERY_STATE", r"D:\studio-agent\ollama\orla\gallery_state.json")
)
# Newest still/clip search roots — media home is ComfyBox only.
MEDIA_ROOTS = [
    IMAGES_DIR,
    VIDEO_DIR,
    COMFYBOX,
]
_SKIP_DIR_PARTS = {
    "user import",
    "user_import",
    "_refined",
    "scene_packs",
    "zip files",
    "unziped originals",
    "temp",
    "rejected",
    "source",
}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_EXT = {".mp4", ".webm", ".mov", ".mkv"}

_PHONETIC_SYSTEM = """
You rewrite book chapter text so Kokoro TTS reads it clearly aloud.
Expand hard names, numbers, abbreviations, and visual-novel tags into plain spoken English.
Keep story meaning and dialogue. Output plain prose only — no markdown, no commentary.
""".strip()


def _skip_path(path: Path) -> bool:
    parts = {x.lower() for x in path.parts}
    return bool(parts & _SKIP_DIR_PARTS)


def _load_state() -> dict:
    if not STATE_PATH.is_file():
        return {"last_displayed": None, "batch": [], "batch_index": 0}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"last_displayed": None, "batch": [], "batch_index": 0}
    if not isinstance(data, dict):
        return {"last_displayed": None, "batch": [], "batch_index": 0}
    data.setdefault("last_displayed", None)
    data.setdefault("batch", [])
    data.setdefault("batch_index", 0)
    return data


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _list_media(roots: list[Path], exts: set[str]) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        # Prefer shallow Images/Video before deep trees.
        candidates = list(root.glob("*"))
        if root.name.lower() not in {"images", "video"}:
            candidates += list(root.rglob("*"))
        for p in candidates:
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
            if _skip_path(p):
                continue
            key = str(p.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(p)
    return found


def _newest(roots: list[Path], exts: set[str]) -> Path | None:
    best: Path | None = None
    best_mtime = -1.0
    for p in _list_media(roots, exts):
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if m > best_mtime:
            best_mtime = m
            best = p
    return best


def _batch_neighbors(path: Path) -> list[Path]:
    """Same-folder files sharing a numeric prefix family, oldest→newest."""
    parent = path.parent
    stem = path.stem
    # studio_edge_00002_ → studio_edge_ ; studio_agent_00007_ → studio_agent_
    m = re.match(r"^(.*?)(\d+)(_?)$", stem)
    if not m:
        return [path]
    prefix = m.group(1)
    siblings: list[Path] = []
    for p in parent.glob(f"{prefix}*{path.suffix}"):
        if not p.is_file() or _skip_path(p):
            continue
        siblings.append(p)
    siblings.sort(key=lambda x: (x.stat().st_mtime, x.name))
    return siblings or [path]


def open_path(path: Path, *, batch: list[Path] | None = None) -> dict:
    if not path.is_file():
        return {"ok": False, "error": f"File not found: {path}"}
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except AttributeError:
        subprocess.Popen(["xdg-open", str(path)])
    except OSError as exc:
        return {"ok": False, "error": str(exc)}

    state = _load_state()
    resolved = str(path.resolve())
    state["last_displayed"] = resolved
    if batch is not None:
        batch_paths = [str(p.resolve()) for p in batch if p.is_file()]
        state["batch"] = batch_paths
        try:
            state["batch_index"] = batch_paths.index(resolved)
        except ValueError:
            state["batch_index"] = 0
    else:
        # Keep existing batch if this file is in it; else rebuild from neighbors.
        existing = [Path(p) for p in state.get("batch") or []]
        if resolved in {str(p.resolve()) for p in existing if p.is_file()}:
            state["batch_index"] = next(
                (i for i, p in enumerate(existing) if str(p.resolve()) == resolved),
                0,
            )
        else:
            neighbors = _batch_neighbors(path)
            state["batch"] = [str(p.resolve()) for p in neighbors]
            try:
                state["batch_index"] = state["batch"].index(resolved)
            except ValueError:
                state["batch_index"] = 0
    _save_state(state)

    kind = "video" if path.suffix.lower() in VIDEO_EXT else "image"
    return {
        "ok": True,
        "action": "open",
        "kind": kind,
        "path": resolved,
        "selector": "path",
        "batch_index": state["batch_index"],
        "batch_size": len(state.get("batch") or []),
        "last_displayed": resolved,
    }


def open_newest(kind: str = "image") -> dict:
    exts = VIDEO_EXT if kind in {"video", "clip"} else IMAGE_EXT
    roots = [VIDEO_DIR if kind in {"video", "clip"} else IMAGES_DIR, COMFYBOX]
    latest = _newest(roots, exts)
    if not latest:
        return {"ok": False, "error": "No media found under ComfyBox Images/Video."}
    result = open_path(latest, batch=_batch_neighbors(latest))
    result["selector"] = "newest"
    return result


def open_last_displayed(kind: str = "image") -> dict:
    state = _load_state()
    raw = state.get("last_displayed")
    if not raw:
        return {
            "ok": False,
            "error": (
                "No last displayed image yet. "
                "Say newest image to open by date, or open something first."
            ),
            "selector": "last_displayed",
        }
    path = Path(raw)
    if not path.is_file():
        return {
            "ok": False,
            "error": f"Last displayed file is missing: {path}",
            "selector": "last_displayed",
        }
    want_video = kind in {"video", "clip"}
    is_video = path.suffix.lower() in VIDEO_EXT
    if want_video != is_video and kind != "any":
        # Still open it — user said last image/video of what was shown.
        pass
    result = open_path(path)
    result["selector"] = "last_displayed"
    return result


def open_batch_step(delta: int, kind: str = "image") -> dict:
    state = _load_state()
    batch = [Path(p) for p in state.get("batch") or [] if Path(p).is_file()]
    if not batch:
        # Seed from last displayed or newest.
        seed = None
        if state.get("last_displayed") and Path(state["last_displayed"]).is_file():
            seed = Path(state["last_displayed"])
        else:
            exts = VIDEO_EXT if kind in {"video", "clip"} else IMAGE_EXT
            seed = _newest([IMAGES_DIR, VIDEO_DIR], exts)
        if seed is None:
            return {"ok": False, "error": "No batch to walk. Open an image first."}
        batch = _batch_neighbors(seed)
        state["batch"] = [str(p.resolve()) for p in batch]
        state["batch_index"] = 0
        if state.get("last_displayed"):
            try:
                state["batch_index"] = state["batch"].index(
                    str(Path(state["last_displayed"]).resolve())
                )
            except ValueError:
                pass
        _save_state(state)

    idx = int(state.get("batch_index") or 0) + delta
    if idx < 0:
        return {
            "ok": False,
            "error": "Already at the first image in this batch.",
            "batch_index": 0,
            "batch_size": len(batch),
        }
    if idx >= len(batch):
        return {
            "ok": False,
            "error": "Already at the last image in this batch.",
            "batch_index": len(batch) - 1,
            "batch_size": len(batch),
        }
    result = open_path(batch[idx], batch=batch)
    result["selector"] = "next" if delta > 0 else "previous"
    return result


def ingest_comfy(body: dict) -> dict:
    """Pull ComfyUI /view output into ComfyBox Images or Video (+ prompt sidecar)."""
    filename = (body.get("filename") or "").strip()
    if not filename:
        return {"ok": False, "error": "filename required"}
    comfy = (body.get("comfyui_url") or "http://192.168.50.57:8188").rstrip("/")
    subfolder = (body.get("subfolder") or "").strip()
    ftype = (body.get("type") or "output").strip() or "output"
    suffix = Path(filename).suffix.lower()
    if suffix in VIDEO_EXT:
        dest_dir = VIDEO_DIR
    else:
        dest_dir = IMAGES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(filename).name

    qs = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": ftype}
    )
    view_url = f"{comfy}/view?{qs}"
    try:
        req = urllib.request.Request(view_url, method="GET")
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": f"ComfyUI download failed: {exc}", "url": view_url}
    if not data:
        return {"ok": False, "error": "ComfyUI returned empty file", "url": view_url}
    dest.write_bytes(data)

    meta = {
        "asked": body.get("asked") or body.get("description") or "",
        "expanded_prompt": body.get("expanded_prompt") or body.get("prompt") or "",
        "prompt_id": body.get("prompt_id") or "",
        "comfy_filename": filename,
        "comfy_subfolder": subfolder,
        "source": "myra_voice" if body.get("source") is None else body.get("source"),
        "windows_path": str(dest.resolve()),
    }
    sidecar = dest.with_suffix(dest.suffix + ".json")
    try:
        sidecar.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"sidecar write failed: {exc}\n")

    # Optional multi-file batch from one job
    batch_names = body.get("batch") or [filename]
    batch_paths: list[Path] = []
    for name in batch_names:
        p = dest_dir / Path(str(name)).name
        if p.is_file():
            batch_paths.append(p)
    if not batch_paths:
        batch_paths = [dest]

    state = _load_state()
    state["batch"] = [str(p.resolve()) for p in batch_paths]
    try:
        state["batch_index"] = state["batch"].index(str(dest.resolve()))
    except ValueError:
        state["batch_index"] = 0
    _save_state(state)

    return {
        "ok": True,
        "action": "ingest",
        "path": str(dest.resolve()),
        "sidecar": str(sidecar),
        "bytes": len(data),
        "batch_size": len(state["batch"]),
        "asked": meta["asked"],
        "expanded_prompt": meta["expanded_prompt"],
    }


def _ollama_chat(system: str, user: str, *, timeout_s: float = 180.0) -> str:
    payload = {
        "model": ORLA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.3, "num_predict": 8192},
    }
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        data = json.loads(r.read().decode("utf-8"))
    return ((data.get("message") or {}).get("content") or "").strip()


def _kokoro_wav(text: str, stem: str) -> str | None:
    if not text or not KOKORO_URL:
        return None
    try:
        req = urllib.request.Request(
            f"{KOKORO_URL}/v1/tts",
            data=json.dumps(
                {
                    "text": text[:8000],
                    "voice": "am_michael",
                    "speed": 0.87,
                    "pause_period_s": 0.45,
                    "pause_comma_s": 0.22,
                    "pause_paragraph_s": 0.7,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            wav = r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        sys.stderr.write(f"Kokoro synth failed: {exc}\n")
        return None
    PHONETIC_OUT.mkdir(parents=True, exist_ok=True)
    dest = PHONETIC_OUT / f"{stem}_phonetic.wav"
    dest.write_bytes(wav)
    return str(dest)


def phonetic_rewrite(body: dict) -> dict:
    text = (body.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "text is required (Myra should send chapter body)"}
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(body.get("stem") or "chapter")).strip("_")
    chapter = body.get("chapter")
    label = f"chapter {chapter}" if chapter else stem
    try:
        rewritten = _ollama_chat(
            _PHONETIC_SYSTEM,
            f"Rewrite this {label} for clear Kokoro read-aloud:\n\n{text}",
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Orla rewrite failed: {exc}"}
    if not rewritten:
        return {"ok": False, "error": "Orla returned empty rewrite"}
    PHONETIC_OUT.mkdir(parents=True, exist_ok=True)
    out = PHONETIC_OUT / f"{stem}_phonetic.txt"
    out.write_text(rewritten + "\n", encoding="utf-8")
    result: dict = {
        "ok": True,
        "action": "phonetic_rewrite",
        "path": str(out),
        "chars": len(rewritten),
        "stem": stem,
    }
    if body.get("also_speak"):
        wav = _kokoro_wav(rewritten, stem)
        if wav:
            result["wav"] = wav
        else:
            result["wav_error"] = "Kokoro not reachable or synth failed"
    return result


def _resolve_selector(body: dict) -> str:
    """Map spoken/request fields to gallery selector."""
    sel = (body.get("selector") or body.get("which") or "").strip().lower()
    if sel in {"last", "last_displayed", "last image", "last video", "displayed"}:
        return "last_displayed"
    if sel in {"newest", "latest", "most recent", "newest image", "newest video"}:
        return "newest"
    if sel in {"next", "forward"}:
        return "next"
    if sel in {"previous", "prev", "back", "backward"}:
        return "previous"
    req = (body.get("request") or body.get("text") or "").lower()
    if re.search(r"\b(?:next|forward)\b", req):
        return "next"
    if re.search(r"\b(?:previous|prev|go back|step back)\b", req):
        return "previous"
    if re.search(r"\b(?:newest|most recent|latest by date)\b", req):
        return "newest"
    # "last image" / "last one displayed" — NOT newest
    if re.search(r"\blast\b", req) and not re.search(r"\bnewest\b", req):
        return "last_displayed"
    if re.search(r"\b(?:latest|most recent)\b", req) and "last" not in req:
        return "newest"
    return "newest"  # default open when unspecified


def handle_action(body: dict) -> dict:
    action = (body.get("action") or "status").strip().lower()
    if action == "status":
        state = _load_state()
        return {
            "ok": True,
            "service": "orla_tools",
            "port": PORT,
            "comfybox": str(COMFYBOX),
            "images_dir": str(IMAGES_DIR),
            "video_dir": str(VIDEO_DIR),
            "media_roots": [str(p) for p in MEDIA_ROOTS if p.exists()],
            "last_displayed": state.get("last_displayed"),
            "batch_size": len(state.get("batch") or []),
            "batch_index": state.get("batch_index"),
            "vocab": {
                "last_image": "last one displayed",
                "newest_image": "by file date/time",
                "next_previous": "walk current batch in creation order",
            },
            "phonetic_out": str(PHONETIC_OUT),
            "kokoro_url": KOKORO_URL,
        }
    if action in {"ingest", "pull", "deliver"}:
        return ingest_comfy(body)
    if action in {"open", "display", "show"}:
        raw = (body.get("path") or body.get("file") or "").strip()
        if raw:
            return open_path(Path(raw))
        kind = (body.get("kind") or "image").strip().lower()
        selector = _resolve_selector(body)
        if selector == "last_displayed":
            return open_last_displayed(kind)
        if selector == "next":
            return open_batch_step(1, kind)
        if selector == "previous":
            return open_batch_step(-1, kind)
        return open_newest(kind)
    if action in {"newest", "latest"}:
        kind = (body.get("kind") or "image").strip().lower()
        return open_newest(kind)
    if action in {"last", "last_displayed"}:
        kind = (body.get("kind") or "image").strip().lower()
        return open_last_displayed(kind)
    if action == "next":
        kind = (body.get("kind") or "image").strip().lower()
        return open_batch_step(1, kind)
    if action in {"previous", "prev"}:
        kind = (body.get("kind") or "image").strip().lower()
        return open_batch_step(-1, kind)
    if action == "latest_path":
        kind = (body.get("kind") or "image").strip().lower()
        exts = VIDEO_EXT if kind in {"video", "clip"} else IMAGE_EXT
        latest = _newest([IMAGES_DIR, VIDEO_DIR, COMFYBOX], exts)
        if not latest:
            return {"ok": False, "error": "No recent media found."}
        return {"ok": True, "path": str(latest), "kind": kind, "selector": "newest"}
    if action in {"phonetic_rewrite", "rewrite_phonetic", "phonetic"}:
        return phonetic_rewrite(body)
    return {"ok": False, "error": f"Unknown action: {action}"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/status", "/health"}:
            self._json(200, handle_action({"action": "status"}))
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid json"})
            return
        if urlparse(self.path).path not in {"/", "/action", "/open"}:
            self._json(404, {"ok": False, "error": "not found"})
            return
        if urlparse(self.path).path == "/open" and "action" not in body:
            body["action"] = "open"
        result = handle_action(body if isinstance(body, dict) else {})
        self._json(200 if result.get("ok") else 400, result)


def main() -> int:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Orla tools listening on http://{HOST}:{PORT}", flush=True)
    print(f"Media home: {COMFYBOX}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Orla tools.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

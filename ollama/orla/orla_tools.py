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
# Dedicated vision model on this Windows gallery rig (images live here).
VLM_MODEL = os.environ.get("ORLA_VLM_MODEL", "qwen2.5vl:7b")
PHONETIC_OUT = Path(os.environ.get("ORLA_PHONETIC_DIR", r"D:\studio-agent\orla-phonetic"))
KOKORO_URL = os.environ.get("ORLA_KOKORO_URL", "http://127.0.0.1:8090").rstrip("/")
COMFYBOX = Path(os.environ.get("ORLA_COMFYBOX", r"D:\ComfyBox Images and Videos"))
IMAGES_DIR = Path(os.environ.get("ORLA_IMAGES_DIR", str(COMFYBOX / "Images")))
VIDEO_DIR = Path(os.environ.get("ORLA_VIDEO_DIR", str(COMFYBOX / "Video")))
# Sidecars live here — not next to every PNG (keeps gallery folders clean).
SIDECAR_ROOT = Path(
    os.environ.get("ORLA_SIDECAR_DIR", r"D:\studio-agent\orla-sidecars")
)
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


def _sidecar_path_for(image: Path) -> Path:
    """Stable sidecar path under SIDECAR_ROOT (never beside the PNG)."""
    import hashlib

    resolved = image.resolve()
    try:
        rel = resolved.relative_to(COMFYBOX.resolve())
        key = str(rel).replace("\\", "__").replace("/", "__")
    except ValueError:
        key = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()
    return SIDECAR_ROOT / f"{key}.json"


def _write_sidecar(image: Path, meta: dict) -> Path:
    path = _sidecar_path_for(image)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return path


def _read_sidecar(image: Path) -> tuple[Path | None, dict]:
    """Prefer cache dir; fall back to legacy image.png.json (read-only)."""
    cached = _sidecar_path_for(image)
    if cached.is_file():
        try:
            return cached, json.loads(cached.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    legacy = image.with_suffix(image.suffix + ".json")
    if legacy.is_file():
        try:
            return legacy, json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return None, {}


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
        "cast": body.get("cast"),
        "batch_id": body.get("batch_id") or "",
    }
    sidecar: Path | None = None
    try:
        sidecar = _write_sidecar(dest, meta)
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


_VLM_TAG_PROMPT = (
    "Look at the image. Reply with ONLY a comma-separated Danbooru/Illustrious "
    "tag list for img2img — no headings, no labels like 'pose:' or 'hair:'. "
    "Include: 1girl/solo if applicable, body pose, framing as VIEW words only "
    "(side view, from behind, man's POV, looking at viewer — never 'camera'), "
    "hair color/length, eye color, clothing or nudity, setting, lighting. "
    "For sexual acts use vulgar explicit tags (fingering her pussy, "
    "fingers in pussy, masturbation, doggystyle, anal penetration, deepthroat). "
    "No soft euphemisms. Example: 1girl, solo, looking at viewer, long white "
    "hair, green eyes, nude, fingering her pussy, bedroom, from front"
)
_VLM_DESC_PROMPT = (
    "Describe this image in 2-4 plain sentences: who/what, pose, scene, lighting. "
    "Be concrete. No markdown."
)


def describe_image(body: dict) -> dict:
    """Vision caption on the Windows gallery rig (qwen2.5vl by default)."""
    import base64

    raw = (body.get("path") or body.get("file") or "").strip()
    if not raw:
        resolved = resolve_media(body)
        if not resolved.get("ok"):
            return resolved
        raw = str(resolved["path"])
    path = Path(raw)
    if not path.is_file():
        return {"ok": False, "error": f"File not found: {raw}"}
    if path.suffix.lower() not in IMAGE_EXT:
        return {"ok": False, "error": f"Not an image: {path.name}"}

    mode = (body.get("mode") or "tags").strip().lower()
    user_prompt = (body.get("prompt") or "").strip()
    if not user_prompt:
        user_prompt = _VLM_TAG_PROMPT if mode in {"tags", "prompt", "danbooru"} else _VLM_DESC_PROMPT

    # Keep payload reasonable for local VLM
    try:
        from PIL import Image
        import io

        im = Image.open(path).convert("RGB")
        im.thumbnail((1280, 1280))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=88)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")

    model = (body.get("model") or VLM_MODEL).strip()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": user_prompt,
                "images": [b64],
            }
        ],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.2, "num_predict": 512},
    }
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"VLM failed: {exc}", "path": str(path), "model": model}

    text = ((data.get("message") or {}).get("content") or "").strip()
    if not text:
        return {"ok": False, "error": "VLM returned empty caption", "path": str(path), "model": model}
    # Collapse prose newlines for tag mode
    if mode in {"tags", "prompt", "danbooru"}:
        text = re.sub(r"\s*\n+\s*", ", ", text)
        text = re.sub(r",\s*,+", ", ", text).strip(" ,")
    return {
        "ok": True,
        "action": "describe_image",
        "path": str(path.resolve()),
        "model": model,
        "mode": mode,
        "description": text,
    }


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


HANDOFF_PATH = Path(
    os.environ.get("ORLA_HANDOFF_STATE", r"D:\studio-agent\ollama\orla\handoff_state.json")
)
_STUDIO_ID_NAME_RE = re.compile(
    r"^studio_(?:agent|edge)_(?:0*)(?P<n>\d+)\b",
    re.I,
)


def _canonical_studio_id(sel: str) -> str:
    """Normalize studio_edge_N / studio_agent_N → studio_agent_NNNNN."""
    s = (sel or "").strip().lower().rstrip("_")
    m = _STUDIO_ID_NAME_RE.match(s)
    if not m:
        return sel
    return f"studio_agent_{int(m.group('n')):05d}"


def _parse_studio_agent_id(text: str) -> str | None:
    """Extract studio_agent_NNNNN from spoken/typed selectors."""
    t = (text or "").strip().lower()
    if not t:
        return None
    m = _STUDIO_ID_NAME_RE.match(t.rstrip("_"))
    if m:
        return f"studio_agent_{int(m.group('n')):05d}"
    m = re.search(
        r"\bstudio\s*(?:agent|edge)\s*(?:number\s+|num\s+|no\.?\s+)?(?:zero\s*)*0*(\d{1,5})\b",
        t,
    )
    if m:
        return f"studio_agent_{int(m.group(1)):05d}"
    # Bare padded id: 00009 / 9 (only when clearly an id, not a sentence)
    m = re.fullmatch(r"0*(\d{1,5})", t)
    if m:
        return f"studio_agent_{int(m.group(1)):05d}"
    return None


def _resolve_selector(body: dict) -> str:
    """Map spoken/request fields to gallery selector (canonical: studio_agent_N)."""
    sel = (body.get("selector") or body.get("which") or "").strip().lower()
    parsed = _parse_studio_agent_id(sel)
    if parsed:
        return parsed
    if sel in {"last", "last_displayed", "last image", "last video", "displayed"}:
        return "last_displayed"
    if sel in {"newest", "latest", "most recent", "newest image", "newest video"}:
        return "newest"
    if sel in {"next", "forward"}:
        return "next"
    if sel in {"previous", "prev", "back", "backward"}:
        return "previous"
    req = (body.get("request") or body.get("text") or "").lower()
    parsed = _parse_studio_agent_id(req)
    if parsed:
        return parsed
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


def _find_studio_agent(stem: str) -> Path | None:
    """Find studio_agent_NNNNN.png. Prefer agent over legacy studio_edge_ same number."""
    want = _canonical_studio_id(stem)
    m = _STUDIO_ID_NAME_RE.match(want)
    if not m:
        return None
    n = int(m.group("n"))
    agent_names = {f"studio_agent_{n:05d}", f"studio_agent_{n}"}
    edge_names = {f"studio_edge_{n:05d}", f"studio_edge_{n}"}

    agent_hit: Path | None = None
    edge_hit: Path | None = None

    def _scan(p: Path) -> None:
        nonlocal agent_hit, edge_hit
        if not p.is_file() or p.suffix.lower() not in IMAGE_EXT:
            return
        name = p.stem.lower().rstrip("_")
        is_agent = name in agent_names or name.startswith(f"studio_agent_{n:05d}")
        is_edge = name in edge_names or name.startswith(f"studio_edge_{n:05d}")
        if not is_agent and not is_edge and re.search(
            rf"studio_(?:agent|edge)_0*{n}\b", name
        ):
            # Embedded ids (bj7_comfy_studio_agent_00031_) — treat as agent family
            is_agent = "studio_agent" in name
            is_edge = (not is_agent) and "studio_edge" in name
        try:
            if is_agent:
                if agent_hit is None or p.stat().st_mtime > agent_hit.stat().st_mtime:
                    agent_hit = p
            elif is_edge:
                if edge_hit is None or p.stat().st_mtime > edge_hit.stat().st_mtime:
                    edge_hit = p
        except OSError:
            if is_agent:
                agent_hit = p
            elif is_edge:
                edge_hit = p

    for p in _list_media([IMAGES_DIR, COMFYBOX], IMAGE_EXT):
        _scan(p)
    user_import = COMFYBOX / "User Import"
    if user_import.is_dir():
        for p in user_import.rglob("*"):
            _scan(p)
    return agent_hit or edge_hit


# Back-compat alias
_find_studio_edge = _find_studio_agent


def resolve_media(body: dict) -> dict:
    """Resolve last/newest/studio_agent_NNNN to a path (no open)."""
    kind = (body.get("kind") or "image").strip().lower()
    exts = VIDEO_EXT if kind in {"video", "clip"} else IMAGE_EXT
    selector = _resolve_selector(body)
    if selector.startswith("studio_agent_") or selector.startswith("studio_edge_"):
        selector = _canonical_studio_id(selector)
        path = _find_studio_agent(selector)
        if not path:
            return {"ok": False, "error": f"No file matching {selector}.", "selector": selector}
        return {
            "ok": True,
            "action": "resolve",
            "path": str(path.resolve()),
            "selector": selector,
            "kind": kind,
        }
    if selector == "last_displayed":
        state = _load_state()
        raw = state.get("last_displayed")
        if raw and Path(raw).is_file():
            return {
                "ok": True,
                "action": "resolve",
                "path": str(Path(raw).resolve()),
                "selector": "last_displayed",
                "kind": kind,
            }
        # Fall through to newest
        selector = "newest"
    latest = _newest([IMAGES_DIR, VIDEO_DIR, COMFYBOX], exts)
    if not latest:
        return {"ok": False, "error": "No media found.", "selector": selector}
    return {
        "ok": True,
        "action": "resolve",
        "path": str(latest.resolve()),
        "selector": selector,
        "kind": kind,
    }


def _extract_comfy_png_meta(path: Path) -> dict:
    """Pull positive/negative/checkpoint/LoRAs from Comfy workflow embedded in PNG."""
    try:
        from PIL import Image
    except ImportError:
        return {}
    try:
        im = Image.open(path)
        raw = (im.info or {}).get("prompt") or (getattr(im, "text", None) or {}).get("prompt")
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        wf = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(wf, dict):
        return {}

    positives: list[str] = []
    negatives: list[str] = []
    loras: list[dict] = []
    ckpt = ""
    width = height = steps = None
    cfg = None
    for _nid, node in wf.items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type") or ""
        inp = node.get("inputs") or {}
        if ct == "CLIPTextEncode":
            text = str(inp.get("text") or "").strip()
            if not text:
                continue
            # Heuristic: negative nodes usually mention bad anatomy / lowres
            low = text.lower()
            if any(
                k in low
                for k in ("lowres", "bad anatomy", "worst quality", "watermark", "bad hands")
            ) and len(text) < 400:
                negatives.append(text)
            else:
                positives.append(text)
        elif ct == "CheckpointLoaderSimple":
            ckpt = str(inp.get("ckpt_name") or ckpt)
        elif ct == "LoraLoader":
            name = str(inp.get("lora_name") or "").strip()
            if name:
                loras.append(
                    {
                        "file": name,
                        "weight": float(inp.get("strength_model") or 0.8),
                    }
                )
        elif ct == "EmptyLatentImage":
            width = inp.get("width", width)
            height = inp.get("height", height)
        elif ct == "KSampler":
            steps = inp.get("steps", steps)
            cfg = inp.get("cfg", cfg)

    positive = max(positives, key=len) if positives else ""
    negative = max(negatives, key=len) if negatives else ""
    if not positive:
        return {}

    cast = None
    m = re.search(r"\b(nb_[a-z0-9_]+)\b", positive, re.I)
    if m:
        cast = m.group(1).lower()

    return {
        "asked": f"(from PNG) {path.name}",
        "expanded_prompt": positive,
        "negative_prompt": negative,
        "checkpoint": ckpt,
        "loras": loras,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg": cfg,
        "cast": cast,
        "source": "png_comfy_workflow",
        "windows_path": str(path.resolve()),
        "comfy_filename": path.name,
    }


def _sidecar_usable(meta: dict) -> bool:
    exp = str((meta or {}).get("expanded_prompt") or (meta or {}).get("nari_expanded") or "").strip()
    if len(exp) < 24:
        return False
    if any(
        x in exp
        for x in (
            "Do not invent",
            "Scene request:",
            "Keep trigger token",
            "Misrouted",
            "Prior prompt to respect",
        )
    ):
        return False
    return True


def get_meta(body: dict) -> dict:
    """Read PNG sidecar JSON; if missing/unusable, extract Comfy workflow from PNG and backfill."""
    raw = (body.get("path") or body.get("file") or "").strip()
    if not raw:
        resolved = resolve_media(body)
        if not resolved.get("ok"):
            return resolved
        raw = str(resolved["path"])
    path = Path(raw)
    if not path.is_file():
        return {"ok": False, "error": f"File not found: {raw}"}
    sidecar, meta = _read_sidecar(path)

    write_back = bool(body.get("backfill", True))
    if not _sidecar_usable(meta) and path.suffix.lower() in IMAGE_EXT:
        extracted = _extract_comfy_png_meta(path)
        if extracted:
            # Keep any non-empty asked from old sidecar
            if meta.get("asked") and not str(meta.get("asked")).startswith("(from PNG)"):
                extracted["asked"] = meta["asked"]
            if meta.get("cast") and not extracted.get("cast"):
                extracted["cast"] = meta["cast"]
            meta = extracted
            if write_back:
                try:
                    sidecar = _write_sidecar(path, meta)
                except OSError as exc:
                    sys.stderr.write(f"sidecar backfill failed: {exc}\n")

    return {
        "ok": True,
        "action": "get_meta",
        "path": str(path.resolve()),
        "sidecar": str(sidecar) if sidecar and sidecar.is_file() else None,
        "meta": meta,
        "usable_prompt": _sidecar_usable(meta),
    }


def upload_to_comfy(body: dict) -> dict:
    """Upload a local gallery/user image into ComfyUI input/ (Pi can't read D:\\)."""
    raw = (body.get("path") or body.get("file") or "").strip()
    if not raw:
        resolved = resolve_media(body)
        if not resolved.get("ok"):
            return resolved
        raw = str(resolved["path"])
    path = Path(raw)
    if not path.is_file():
        return {"ok": False, "error": f"File not found: {raw}"}
    comfy = (body.get("comfyui_url") or "http://192.168.50.57:8188").rstrip("/")
    boundary = f"----OrlaBoundary{os.urandom(8).hex()}"
    filename = path.name
    file_bytes = path.read_bytes()
    body_parts = []
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode("utf-8")
        + file_bytes
        + b"\r\n"
    )
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
        f"true\r\n".encode("utf-8")
    )
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    data = b"".join(body_parts)
    req = urllib.request.Request(
        f"{comfy}/upload/image",
        data=data,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(data)),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"Comfy upload failed: {exc}", "path": str(path)}
    name = str(resp.get("name") or filename)
    return {
        "ok": True,
        "action": "upload_to_comfy",
        "path": str(path.resolve()),
        "comfy_image": name,
        "comfyui_url": comfy,
        "bytes": len(file_bytes),
    }


def backfill_sidecars(body: dict) -> dict:
    """Scan Images (or a path) and write sidecars from embedded Comfy PNG workflows."""
    root = Path(body.get("dir") or IMAGES_DIR)
    if not root.is_dir():
        return {"ok": False, "error": f"Not a directory: {root}"}
    written = 0
    skipped = 0
    failed = 0
    examples: list[str] = []
    for p in sorted(root.glob("*.png")) + sorted(root.glob("*.jpg")) + sorted(root.glob("*.webp")):
        r = get_meta({"path": str(p), "backfill": True})
        if not r.get("ok"):
            failed += 1
            continue
        if r.get("usable_prompt") and r.get("sidecar"):
            # Count newly usable
            meta = r.get("meta") or {}
            if meta.get("source") == "png_comfy_workflow" or Path(r["sidecar"]).is_file():
                if meta.get("source") == "png_comfy_workflow":
                    written += 1
                    if len(examples) < 5:
                        examples.append(p.name)
                else:
                    skipped += 1
            else:
                skipped += 1
        else:
            failed += 1
    return {
        "ok": True,
        "action": "backfill_sidecars",
        "dir": str(root),
        "written_or_refreshed": written,
        "skipped": skipped,
        "failed": failed,
        "examples": examples,
    }


def handoff_event(body: dict) -> dict:
    """Nari↔Orla bus: record job events; optional auto-display on display_please."""
    state = {}
    if HANDOFF_PATH.is_file():
        try:
            state = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}
    event = {
        "from": body.get("from") or "nari",
        "to": body.get("to") or "orla",
        "event": (body.get("event") or "done").strip().lower(),
        "path": body.get("path") or "",
        "prompt_id": body.get("prompt_id") or "",
        "cast_id": body.get("cast_id"),
        "batch_id": body.get("batch_id") or "",
        "ts": __import__("time").time(),
    }
    history = list(state.get("history") or [])
    history.append(event)
    state["history"] = history[-40:]
    state["last"] = event
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    opened = None
    if event["event"] in {"display_please", "done"} and body.get("auto_display"):
        if event["path"] and Path(event["path"]).is_file():
            opened = open_path(Path(event["path"]))
        else:
            opened = open_newest("image")
    # display_please always tries to open path or newest
    if event["event"] == "display_please" and opened is None:
        if event["path"] and Path(event["path"]).is_file():
            opened = open_path(Path(event["path"]))
        else:
            opened = open_newest("image")

    return {
        "ok": True,
        "action": "handoff",
        "event": event,
        "opened": opened,
    }


def handle_action(body: dict) -> dict:
    action = (body.get("action") or "status").strip().lower()
    if action == "status":
        state = _load_state()
        handoff = {}
        if HANDOFF_PATH.is_file():
            try:
                handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8")).get("last") or {}
            except (OSError, json.JSONDecodeError):
                handoff = {}
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
            "last_handoff": handoff,
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
    if action in {"resolve", "resolve_media"}:
        return resolve_media(body)
    if action in {"get_meta", "meta", "sidecar"}:
        return get_meta(body)
    if action in {"backfill_sidecars", "backfill", "repair_sidecars"}:
        return backfill_sidecars(body)
    if action in {"upload_to_comfy", "upload_image", "prepare_img2img"}:
        return upload_to_comfy(body)
    if action in {"describe_image", "vlm", "caption", "see_image"}:
        return describe_image(body)
    if action in {"handoff", "notify", "job_event"}:
        return handoff_event(body)
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

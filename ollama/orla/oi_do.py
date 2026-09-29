#!/usr/bin/env python3
"""Tiny Open Interpreter CLI for Orla — one command per job, no guessing.

Usage (from Open Interpreter shell tool):
  py -3 D:\\studio-agent\\ollama\\orla\\oi_do.py write-doc <name.md> <text>
  py -3 D:\\studio-agent\\ollama\\orla\\oi_do.py open-folder [alias-or-path]
  py -3 D:\\studio-agent\\ollama\\orla\\oi_do.py comfybox-status
  py -3 D:\\studio-agent\\ollama\\orla\\oi_do.py nari-jobs
  py -3 D:\\studio-agent\\ollama\\orla\\oi_do.py ask-nari "is the Comfy queue clear?"
  py -3 D:\\studio-agent\\ollama\\orla\\oi_do.py proofread "paste the text here"

write-doc always lands in D:\\Bad boy\\TheaterJobs\\staging\\orla_docs
open-folder only opens paths under D:\\Bad boy\\TheaterJobs
There is no delete command. Do not invent one.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

WORK_ROOT = Path(os.environ.get("ORLA_WORK_ROOT", r"D:\Bad boy\TheaterJobs"))
DOCS_DIR = WORK_ROOT / "staging" / "orla_docs"
FOLDER_ALIASES = {
    "work": WORK_ROOT,
    "theaterjobs": WORK_ROOT,
    "theater-jobs": WORK_ROOT,
    "theater jobs": WORK_ROOT,
    "project": WORK_ROOT,
    "docs": DOCS_DIR,
    "drafts": DOCS_DIR,
    "orla": DOCS_DIR,
    "orla_docs": DOCS_DIR,
    "staging": WORK_ROOT / "staging",
    "candidates": WORK_ROOT / "staging" / "candidates",
    "approved": WORK_ROOT / "staging" / "approved",
    "game": WORK_ROOT / "game",
}

MYRA = "myra"
NARI_OLLAMA = "http://192.168.50.57:11434"
COMFY = "http://192.168.50.57:8188"
NARI_MODEL = "nari"


def _http_json(url: str, payload: dict | None = None, timeout: float = 30.0):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": str(exc), "url": url}


def comfybox_status() -> int:
    """Tell Myra to put ComfyBox status on her panel."""
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        MYRA,
        "/home/james/studio-edge-venv/bin/python",
        "/home/james/studio-edge/show_comfybox_status.py",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    out = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    print(out or f"ssh exit {proc.returncode}")
    return proc.returncode


def nari_jobs() -> int:
    queue = _http_json(f"{COMFY}/queue", timeout=8)
    stats = _http_json(f"{COMFY}/system_stats", timeout=8)
    running = queue.get("queue_running") if isinstance(queue, dict) else None
    pending = queue.get("queue_pending") if isinstance(queue, dict) else None
    n_run = len(running) if isinstance(running, list) else "?"
    n_pend = len(pending) if isinstance(pending, list) else "?"
    print(json.dumps({"queue_running": n_run, "queue_pending": n_pend, "queue": queue, "system_stats": stats}, indent=2)[:4000])
    return 0 if isinstance(queue, dict) and "error" not in queue else 1


def ask_nari(text: str) -> int:
    body = {
        "model": NARI_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Nari on ComfyBox. Short practical answers. "
                    "You own create / Forge / Wan. You do not upscale (that is Orla)."
                ),
            },
            {"role": "user", "content": text},
        ],
    }
    result = _http_json(f"{NARI_OLLAMA}/api/chat", body, timeout=120)
    if not isinstance(result, dict) or result.get("error"):
        print(json.dumps(result, indent=2))
        return 1
    msg = (result.get("message") or {}).get("content") or result.get("response") or ""
    print(msg.strip() or json.dumps(result)[:2000])
    return 0


def proofread(text: str) -> int:
    """Local grammar pass — Orla should do this in-chat; this is a fallback."""
    print("PROOFREAD_FALLBACK: do this in-chat as Orla, do not shell out.")
    print(text)
    return 0


def _under_work(path: Path) -> bool:
    try:
        path.resolve().relative_to(WORK_ROOT.resolve())
        return True
    except ValueError:
        return False


def _safe_doc_name(raw: str) -> str | None:
    name = Path(raw.strip().replace("\\", "/")).name
    if not name or name in {".", ".."}:
        return None
    stem, ext = os.path.splitext(name)
    if not stem or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,80}", stem):
        return None
    ext = ext.lower()
    if ext not in {".md", ".txt"}:
        ext = ".md"
    return stem + ext


def write_doc(name: str, text: str) -> int:
    safe = _safe_doc_name(name)
    if not safe:
        print("REFUSED: document name must be a simple .md or .txt filename")
        return 2
    if not text.strip():
        print("usage: oi_do.py write-doc <name.md> <text>")
        return 2
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    dest = (DOCS_DIR / safe).resolve()
    if not _under_work(dest):
        print("REFUSED: path escaped the TheaterJobs work folder")
        return 2
    existed = dest.exists()
    dest.write_text(text, encoding="utf-8", newline="\n")
    print(f"CREATED: {dest}" if not existed else f"UPDATED: {dest}")
    print(f"LOCATION: {dest.parent}")
    return 0


def open_folder(spec: str) -> int:
    raw = (spec or "docs").strip().strip('"')
    key = raw.lower()
    if key in FOLDER_ALIASES:
        target = FOLDER_ALIASES[key]
    else:
        candidate = Path(raw)
        target = candidate if candidate.is_absolute() else (WORK_ROOT / raw)
    try:
        target = target.resolve()
    except OSError as exc:
        print(f"REFUSED: {exc}")
        return 2
    if not _under_work(target) and target != WORK_ROOT.resolve():
        print(f"REFUSED: {target} is outside D:\\Bad boy\\TheaterJobs")
        return 2
    if not target.exists():
        if target == DOCS_DIR.resolve():
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
        else:
            print(f"MISSING: {target}")
            return 1
    print(f"LOCATION: {target}")
    if target.is_file():
        subprocess.Popen(["explorer.exe", "/select,", str(target)])
    else:
        subprocess.Popen(["explorer.exe", str(target)])
    print("OPENED: Explorer")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help", "help"}:
        print(__doc__.strip())
        return 0
    cmd = argv[1].strip().lower()
    if cmd in {"delete", "rm", "remove", "rmdir", "del", "unlink"}:
        print("REFUSED: Orla cannot delete files or folders.")
        return 2
    rest = " ".join(argv[2:]).strip()
    if cmd in {"comfybox-status", "status", "show-status"}:
        return comfybox_status()
    if cmd in {"nari-jobs", "jobs", "queue"}:
        return nari_jobs()
    if cmd in {"ask-nari", "nari"}:
        if not rest:
            print("usage: oi_do.py ask-nari <message>")
            return 2
        return ask_nari(rest)
    if cmd in {"proofread", "grammar"}:
        return proofread(rest)
    if cmd in {"write-doc", "create-doc", "save-doc", "document"}:
        if len(argv) < 3:
            print("usage: oi_do.py write-doc <name.md> <text>")
            return 2
        name = argv[2]
        text = " ".join(argv[3:]).strip()
        if not text and not sys.stdin.isatty():
            text = sys.stdin.read()
        return write_doc(name, text)
    if cmd in {"open-folder", "open", "show-folder", "show-location", "reveal"}:
        return open_folder(rest)
    print(f"unknown command: {cmd}")
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

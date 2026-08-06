#!/usr/bin/env python3
"""Watch ComfyBox still folders; ask Orla tools to checklist-review new PNGs.

Reports land under:
  D:\\ComfyBox Images and Videos\\Images\\vlm_reports\\<relative>\\<stem>.json
  D:\\ComfyBox Images and Videos\\Images\\vlm_reports\\<relative>\\<stem>.md

Usage:
  py -3 watch_stills_vlm.py
  py -3 watch_stills_vlm.py --once
  py -3 watch_stills_vlm.py --dirs story_stills_v1 scene_match_comfy_v2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

IMAGES = Path(r"D:\ComfyBox Images and Videos\Images")
TOOLS = "http://127.0.0.1:11436/action"
DEFAULT_DIRS = [
    "story_stills_v1",
    "scene_match_comfy_v2",
    "scene_match_comfy",
]
STATE_PATH = Path(r"D:\studio-agent\ollama\orla\vlm_watch_state.json")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _post(body: dict, timeout_s: float = 300.0) -> dict:
    req = urllib.request.Request(
        TOOLS,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        return json.loads(r.read().decode("utf-8"))


def _load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"done": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _expected_from_name(path: Path) -> str:
    """Cheap beat hint from filename for watcher (gen agent should pass richer expected)."""
    stem = path.stem.replace("_", " ")
    return f"Filename beat hint: {stem}. Score identity/pose/act against that hint."


def scan_and_review(dirs: list[str], *, force: bool = False) -> int:
    state = _load_state()
    done: dict = state.setdefault("done", {})
    n = 0
    for dname in dirs:
        root = IMAGES / dname
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXT:
                continue
            # Skip report folders / junk
            if "vlm_reports" in path.parts:
                continue
            key = str(path.resolve())
            mtime = path.stat().st_mtime
            prev = done.get(key)
            if not force and prev is not None and float(prev) >= mtime:
                continue
            print(f"Reviewing {path} ...", flush=True)
            try:
                result = _post(
                    {
                        "action": "review_still",
                        "path": str(path),
                        "expected": _expected_from_name(path),
                        "write_report": True,
                    }
                )
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                print(f"  FAIL transport: {exc}", flush=True)
                continue
            if not result.get("ok"):
                print(f"  FAIL: {result.get('error')}", flush=True)
                continue
            overall = (result.get("report") or {}).get("overall") or "?"
            report_json = result.get("report_json")
            print(f"  {overall} -> {report_json}", flush=True)
            done[key] = mtime
            n += 1
            _save_state(state)
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Orla VLM still watcher")
    ap.add_argument(
        "--dirs",
        nargs="*",
        default=DEFAULT_DIRS,
        help="Subfolders under ComfyBox Images to watch",
    )
    ap.add_argument("--once", action="store_true", help="Single scan then exit")
    ap.add_argument("--force", action="store_true", help="Re-review already done files")
    ap.add_argument("--interval", type=float, default=8.0, help="Seconds between scans")
    args = ap.parse_args()

    # Health check
    try:
        st = _post({"action": "status"}, timeout_s=5)
        if not st.get("ok"):
            print("Orla tools not healthy:", st, file=sys.stderr)
            return 1
        print(
            f"Orla tools OK. VLM default={st.get('vlm_model')} "
            f"watching {args.dirs}",
            flush=True,
        )
    except Exception as exc:
        print(f"Orla tools unreachable at {TOOLS}: {exc}", file=sys.stderr)
        print("Start with: D:\\studio-agent\\ollama\\orla\\start_orla.ps1", file=sys.stderr)
        return 1

    if args.once:
        n = scan_and_review(list(args.dirs), force=args.force)
        print(f"Done. Reviewed {n} image(s).")
        return 0

    print("Watching for new stills (Ctrl+C to stop)...", flush=True)
    while True:
        try:
            scan_and_review(list(args.dirs), force=False)
            time.sleep(max(2.0, args.interval))
        except KeyboardInterrupt:
            print("Stopped.", flush=True)
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

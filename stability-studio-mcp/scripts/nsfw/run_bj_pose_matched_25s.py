# -*- coding: utf-8 -*-
"""Pose-matched D-style loop (~19s bobbing) + oral creampie/money-shot → ~25s."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

from studio.config import load_config, catalog_path
from studio.engine import GenerationEngine
from studio.catalog import StyleCatalog
from studio.video_utils import concat_videos, extract_last_frame, probe_video

_spec = importlib.util.spec_from_file_location(
    "run_bj_wan22_loras", ROOT / "scripts" / "run_bj_wan22_loras.py"
)
_wan22 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_wan22)
build_api = _wan22.build_api

VIDEO_DIR = Path(r"D:\ComfyBox Images and Videos\Video")
IMPORT_DIR = Path(r"D:\ComfyBox Images and Videos\User Import")
COMPARE = VIDEO_DIR / "compare"
WORK = COMPARE / "_pose_work"
SRC_12 = VIDEO_DIR / "studio_agent_wan22_sq_12s.mp4"
BOBBING = VIDEO_DIR / "studio_agent_wan22_sq_bobbing19.mp4"
FINAL = VIDEO_DIR / "studio_agent_wan22_sq_25s.mp4"
SIZE = 720
TARGET_BOB_SEC = 19.0
REWIND_MAX = 12  # frames


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _extract_all_frames(video: Path, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for old in dest_dir.glob("f_*.png"):
        old.unlink()
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            str(dest_dir / "f_%04d.png"),
        ]
    )
    return sorted(dest_dir.glob("f_*.png"))


def _gray_small(path: Path, size: int = 96) -> np.ndarray:
    im = Image.open(path).convert("L").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.asarray(im, dtype=np.float32)
    return arr - arr.mean()


def _best_loop_points(frames: list[Path], half_idx: int) -> tuple[int, int, float]:
    """
    Find (start_i, end_i) near [0, half] with end within REWIND_MAX of half,
    minimizing appearance distance so ping-pong join is quieter (drool/pose).
    """
    n = len(frames)
    half_idx = min(max(half_idx, REWIND_MAX + 2), n - 2)
    # Candidate ends: half_idx-REWIND_MAX .. half_idx
    # Candidate starts: 0 .. REWIND_MAX+8 (near beginning of bob)
    ends = list(range(max(REWIND_MAX, half_idx - REWIND_MAX), half_idx + 1))
    starts = list(range(0, min(REWIND_MAX + 10, half_idx // 3)))
    feats = {i: _gray_small(frames[i]) for i in set(starts + ends)}

    best = (0, half_idx, 1e18)
    for s in starts:
        fs = feats[s]
        for e in ends:
            if e - s < 24:  # need enough motion (~1.5s)
                continue
            fe = feats[e]
            # MSE + light edge emphasis via gradient
            err = float(np.mean((fs - fe) ** 2))
            if err < best[2]:
                best = (s, e, err)
    return best


def _frames_to_video(frames: list[Path], dest: Path, fps: float) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    list_file = dest.with_suffix(".txt")
    # concat demuxer needs same codec — use image2 pipe via ffmpeg pattern if contiguous
    # Copy selected frames to sequential names
    seq = WORK / f"seq_{dest.stem}"
    if seq.exists():
        for p in seq.glob("*"):
            p.unlink()
    else:
        seq.mkdir(parents=True)
    for i, fr in enumerate(frames, start=1):
        target = seq / f"s_{i:04d}.png"
        target.write_bytes(fr.read_bytes())
    _run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(seq / "s_%04d.png"),
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ]
    )
    return dest


def build_pose_matched_bobbing() -> dict:
    WORK.mkdir(parents=True, exist_ok=True)
    COMPARE.mkdir(parents=True, exist_ok=True)
    info = probe_video(SRC_12)
    fps = float(info["fps"])
    frame_paths = _extract_all_frames(SRC_12, WORK / "all_frames")
    n = len(frame_paths)
    half_idx = n // 2  # ~6.125s
    start_i, end_i, err = _best_loop_points(frame_paths, half_idx)
    print(
        f"POSE match: start={start_i} end={end_i} "
        f"(half={half_idx}, rewind={half_idx - end_i} frames, mse={err:.2f})",
        flush=True,
    )

    segment = frame_paths[start_i : end_i + 1]
    fwd = WORK / "matched_fwd.mp4"
    _frames_to_video(segment, fwd, fps)
    rev_frames = list(reversed(segment[1:-1]))  # avoid duplicating turnaround frames
    rev = WORK / "matched_rev.mp4"
    _frames_to_video(rev_frames, rev, fps)

    # D-style cycle: fwd + rev (+ optional fwd), repeat until >= TARGET_BOB_SEC
    cycle_parts = [fwd, rev]
    # One cycle duration
    cycle_dur = probe_video(fwd)["duration_sec"] + probe_video(rev)["duration_sec"]
    parts: list[Path] = []
    dur = 0.0
    cycle_i = 0
    while dur < TARGET_BOB_SEC - 0.05:
        # D pattern: pingpong then half (fwd) — use matched fwd as the "half"
        if cycle_i % 2 == 0:
            chunk = [fwd, rev]
        else:
            chunk = [fwd]
        for c in chunk:
            parts.append(c)
            dur += float(probe_video(c)["duration_sec"])
            if dur >= TARGET_BOB_SEC - 0.05:
                break
        cycle_i += 1
        if cycle_i > 20:
            break

    concat_videos(parts, BOBBING)
    bob_info = probe_video(BOBBING)
    # Also drop a compare copy
    compare_out = COMPARE / "D2_pose_matched_bobbing19.mp4"
    compare_out.write_bytes(BOBBING.read_bytes())
    result = {
        "ok": True,
        "bobbing": str(BOBBING),
        "duration_sec": bob_info["duration_sec"],
        "start_frame": start_i,
        "end_frame": end_i,
        "half_frame": half_idx,
        "rewind_frames": half_idx - end_i,
        "match_mse": err,
        "cycle_sec": cycle_dur,
        "parts": len(parts),
    }
    (ROOT / "outputs" / "bj_pose_matched_bobbing.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("BOBBING", json.dumps(result, indent=2), flush=True)
    return result


def _wait_comfy_idle(eng: GenerationEngine, timeout: float = 120.0) -> None:
    """Best-effort: wait until running queue empties so we don't fight the old finish job."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            q = eng.comfy._get("/queue")  # type: ignore[attr-defined]
        except Exception:
            try:
                import requests

                q = requests.get(f"{eng.comfy.base_url}/queue", timeout=10).json()
            except Exception:
                return
        running = q.get("queue_running") or []
        pending = q.get("queue_pending") or []
        if not running and not pending:
            return
        print(
            f"Waiting for Comfy queue to clear (running={len(running)} pending={len(pending)})",
            flush=True,
        )
        time.sleep(5)


def _interrupt_comfy(eng: GenerationEngine) -> None:
    import requests

    try:
        requests.post(f"{eng.comfy.base_url}/interrupt", timeout=10)
        requests.post(f"{eng.comfy.base_url}/queue", json={"clear": True}, timeout=10)
        print("Interrupted/cleared Comfy queue (old climax from 12s end discarded)", flush=True)
    except Exception as exc:
        print(f"Queue interrupt note: {exc}", flush=True)


def append_climax(eng: GenerationEngine) -> dict:
    beats = [
        {
            "seed": 211,
            "prefix": "studio_agent_wan22_sq25_cream",
            "negative": (
                "pulling away early, empty mouth, no cum, dry mouth, "
                "deflating penis, shrinking penis, disappearing shaft, "
                "chewing, biting, deformed hands, photoreal, identity change, "
                "morphing face, flicker, warped anatomy"
            ),
            "prompt": (
                "oral creampie, she keeps sucking as he cums in her mouth, "
                "thick cum fills her mouth around the shaft, lips sealed on thick erect penis "
                "with constant girth, rhythmic bobbing while cumming, anime style, "
                "same purple hair face framing"
            ),
        },
        {
            "seed": 212,
            "prefix": "studio_agent_wan22_sq25_money",
            "negative": (
                "staying fully inserted, mouth stays closed on shaft, "
                "deflating penis, shrinking penis, disappearing shaft, melting cum, "
                "chewing, deformed hands, photoreal, identity change, morphing face, "
                "flicker, warped anatomy"
            ),
            "prompt": (
                "money shot, she pulls back off the shaft as he finishes, "
                "thick erect penis withdraws from her lips still solid with constant girth, "
                "cum on her tongue lips and chin, open mouth after oral creampie, "
                "anime style, same purple hair face framing"
            ),
        },
    ]
    working = BOBBING
    log = []
    for i, beat in enumerate(beats):
        last = IMPORT_DIR / f"close_up_sq25_finish_last_{i}.png"
        extract_last_frame(working, last)
        print(
            f"CLIMAX beat {i + 1}/2 seed={beat['seed']} "
            f"(current {probe_video(working)['duration_sec']:.2f}s)",
            flush=True,
        )
        uploaded = eng.comfy.upload_image(last)
        api = build_api(
            image_name=uploaded,
            prompt=beat["prompt"],
            negative=beat["negative"],
            width=SIZE,
            height=SIZE,
            length=49,
            steps=20,
            switch_step=10,
            cfg=3.5,
            seed=beat["seed"],
        )
        api["70"]["inputs"]["filename_prefix"] = beat["prefix"]
        prompt_id = eng.comfy.queue_prompt(api)
        history = eng.comfy.wait_for_completion(prompt_id)
        outputs = eng.comfy.collect_outputs(history)
        saved = eng._save_comfy_outputs(
            outputs, extensions=(".mp4", ".webm", ".gif", ".png")
        )
        if not saved:
            raise RuntimeError(f"No climax video for beat {i + 1}")
        cont = Path(saved[0])
        joined = VIDEO_DIR / f"studio_agent_wan22_sq25_build_{i + 1}.mp4"
        concat_videos([working, cont], joined)
        working = joined
        entry = {
            "beat": i + 1,
            "seed": beat["seed"],
            "continuation": str(cont),
            "joined": str(joined),
            "duration_sec": probe_video(working)["duration_sec"],
            "last_frame": str(last),
            "prompt_id": prompt_id,
        }
        log.append(entry)
        print(f"CLIMAX joined → {joined.name} ({entry['duration_sec']:.2f}s)", flush=True)

    FINAL.write_bytes(working.read_bytes())
    compare_final = COMPARE / "FINAL_pose_matched_25s.mp4"
    compare_final.write_bytes(FINAL.read_bytes())
    # workspace mirror
    ws = Path(r"D:\Bad boy\_compare_bj_close")
    if ws.is_dir():
        (ws / "FINAL_pose_matched_25s.mp4").write_bytes(FINAL.read_bytes())
        (ws / "D2_pose_matched_bobbing19.mp4").write_bytes(BOBBING.read_bytes())

    result = {
        "ok": True,
        "bobbing": str(BOBBING),
        "final": str(FINAL),
        "duration_sec": probe_video(FINAL)["duration_sec"],
        "beats": log,
    }
    (ROOT / "outputs" / "bj_pose_matched_25s.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    bob = build_pose_matched_bobbing()
    cfg = load_config()
    eng = GenerationEngine(cfg, StyleCatalog(catalog_path(cfg), cfg))
    eng.comfy.timeout = max(eng.comfy.timeout, 3600)
    _interrupt_comfy(eng)
    time.sleep(2)
    _wait_comfy_idle(eng, timeout=60)
    final = append_climax(eng)
    summary = {"bobbing": bob, "final": final}
    (ROOT / "outputs" / "bj_pose_matched_25s_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("OK", json.dumps(summary, indent=2), flush=True)
    sys.exit(0 if final.get("ok") else 1)


if __name__ == "__main__":
    main()

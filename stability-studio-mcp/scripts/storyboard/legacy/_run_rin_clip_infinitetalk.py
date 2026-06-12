#!/usr/bin/env python3
"""Rin storyboard clip via Wan2GP Infinitetalk (audio-driven lip sync)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

_LEGACY = Path(__file__).resolve().parent
sys.path.insert(0, str(_LEGACY))
from _bootstrap import setup_paths

setup_paths()
MCP_ROOT = setup_paths()
from _env import comfy_python, imageio_ffmpeg

import rin_project_paths as P

P.ensure_layout()
PROJECT_DIR = P.ROOT
FRAME_RATE = 16.0


def _audio_duration(path: Path) -> float:
    py = comfy_python()
    script = r"""
import json, sys
from pathlib import Path
import librosa
p = Path(sys.argv[1])
y, sr = librosa.load(p, sr=None, mono=True)
print(json.dumps(len(y)/sr if sr else 0))
"""
    out = subprocess.run([str(py), "-c", script, str(path)], capture_output=True, text=True, check=True)
    return float(json.loads(out.stdout.strip()))


def build_infinitetalk_settings(
    *,
    prompt: str,
    image_path: Path,
    audio_path: Path,
    video_length: int,
    resolution: str = "832x480",
    seed: int = 424250,
    negative_prompt: str = "",
) -> dict:
    return {
        "settings_version": 2.56,
        "model_type": "infinitetalk",
        "prompt": prompt.strip(),
        "negative_prompt": negative_prompt.strip(),
        "resolution": resolution,
        "video_length": int(video_length),
        "batch_size": 1,
        "seed": int(seed),
        "num_inference_steps": 30,
        "guidance_scale": 5.0,
        "guidance_phases": 1,
        "audio_guidance_scale": 5.0,
        "flow_shift": 7,
        "sample_solver": "euler",
        "repeat_generation": 1,
        "multi_prompts_gen_type": "FG",
        "image_prompt_type": "S",
        "video_prompt_type": "0KI",
        "audio_prompt_type": "A",
        "motion_amplitude": 1.0,
        "sliding_window_size": min(81, int(video_length)),
        "sliding_window_overlap": 9,
        "image_start": str(image_path.resolve()),
        "image_refs": [str(image_path.resolve())],
        "audio_guide": str(audio_path.resolve()),
        "speakers_locations": "0:100",
        "remove_background_images_ref": 0,
    }


CLIP_PRESETS = {
    "1": {
        "out": "Rin_clip1_walk_talk.mp4",
        "log": "rin_clip1_infinitetalk.json",
        "image": "Rin_kitsune_approved.png",
        "audio": "Rin_dialogue_01_greetings.mp3",
        "seed": 424250,
        "prompt": (
            "anime kitsune fox girl Rin, white hair, fox ears, white tails, dark blue military uniform, "
            "walking toward camera on cherry blossom park path, soft daylight, speaking to viewer, "
            "natural lip movement, cinematic"
        ),
        "negative": "blurry, deformed, bad anatomy, static frozen, different character",
        "motion_note": "walk toward camera",
    },
    "2": {
        "out": "Rin_clip2_bow_talk.mp4",
        "log": "rin_clip2_infinitetalk.json",
        "image": "Rin_clip1_last_frame.png",
        "audio": "Rin_dialogue_02_rin_father.mp3",
        "seed": 424251,
        "prompt": (
            "(at 0 seconds: anime kitsune fox girl Rin, navy uniform, cherry blossom park, "
            "begins polite Japanese ojigi bow, hands empty at sides, speaking).\n"
            "(at 1 second: mid-bow, respectful waist bend, tails behind, speaking).\n"
            "(at 2 seconds: rises from bow, empty hands, calm serious expression, speaking)"
        ),
        "negative": (
            "sword, katana, blade, weapon, kunai, dagger, blurry, deformed, bad anatomy, bad hands, "
            "static frozen, different character"
        ),
        "motion_note": "bow only — weapon beat deferred to clip 3 + SFX",
    },
    "3": {
        "out": "Rin_clip3_stab_talk.mp4",
        "log": "rin_clip3_infinitetalk.json",
        "image": "Rin_clip2_last_frame.png",
        "audio": "Rin_dialogue_03_prepare_die.mp3",
        "seed": 424253,
        "prompt": (
            "anime kitsune fox girl Rin, white hair, fox ears, white tails, dark blue military uniform, "
            "lunges toward camera aggressively, arm thrust forward toward viewer, fierce expression, "
            "speaking, cherry blossom park, motion blur, cinematic"
        ),
        "negative": (
            "sword, katana, blade, walking away, blurry, deformed, bad anatomy, bad hands, "
            "static frozen, different character"
        ),
        "motion_note": "lunge/stab + prepare to die",
        "post_fade": "run _run_rin_clip3_fade_black.py on output if needed",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rin Infinitetalk clip")
    parser.add_argument("clip", choices=["1", "2", "3"], help="Storyboard clip number")
    args = parser.parse_args()
    preset = CLIP_PRESETS[args.clip]

    out_log = MCP_ROOT / "outputs" / str(preset["log"])
    try:
        from studio.config import load_config
        from studio.gpu_backend import acquire_gpu_lock, assert_backend_available, release_gpu_lock
        from studio.output_paths import deliver_files
        from studio.wan2gp_assets import wan2gp_root
        from studio.wan2gp_runner import _run_subprocess_api, resolve_wan2gp_python

        image = P.CHAIN / str(preset["image"])
        audio = P.AUDIO / str(preset["audio"])
        if not image.is_file():
            raise FileNotFoundError(image)
        if not audio.is_file():
            raise FileNotFoundError(f"{audio} — run _run_rin_dialogue_chunks.py first")

        dur = _audio_duration(audio)
        video_length = max(33, min(81, int(dur * FRAME_RATE) + 9))

        cfg = load_config()
        cfg.setdefault("gpu_backend", {})["min_free_vram_gb_comfyui"] = 0.05
        runtime = assert_backend_available(cfg, "wan2gp", operation="infinitetalk")
        python = resolve_wan2gp_python(cfg, runtime)
        root = wan2gp_root(cfg)
        if not python or not root.is_dir():
            raise RuntimeError("Wan2GP python/root not resolved — stop Gradio UI on :7860 first")

        settings = build_infinitetalk_settings(
            prompt=str(preset["prompt"]),
            image_path=image,
            audio_path=audio,
            video_length=video_length,
            seed=int(preset["seed"]),
            negative_prompt=str(preset["negative"]),
        )

        print(f"Clip {args.clip} Infinitetalk — {preset['motion_note']}", flush=True)
        print(f"Audio {dur:.2f}s -> {video_length} frames @ {FRAME_RATE}fps", flush=True)

        acquire_gpu_lock(cfg, "wan2gp", detail=f"rin_clip{args.clip}_infinitetalk")
        try:
            payload = _run_subprocess_api(cfg, settings, python, root)
        finally:
            release_gpu_lock(cfg, "wan2gp")

        if not payload.get("success"):
            raise RuntimeError(json.dumps(payload.get("errors") or payload, indent=2))
        saved, delivered = deliver_files(cfg, payload.get("generated_files") or [])
        result = {"success": True, "saved_files": saved, "delivered_files": delivered, "raw": payload}

        saved = result.get("saved_files") or result.get("delivered_files") or []
        dest = P.CLIPS / str(preset["out"])
        if saved:
            shutil.copy2(saved[0], dest)
            result["project_copy"] = str(dest)

        payload = {
            "clip": int(args.clip),
            "status": "success" if result.get("success") else "failed",
            "audio_duration_s": dur,
            "video_length": video_length,
            "settings": settings,
            "result": result,
        }
        out_log.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        shutil.copy2(out_log, P.LOGS / str(preset["log"]))
        print(json.dumps(payload, indent=2))
        return 0 if result.get("success") else 1
    except Exception:
        err = traceback.format_exc()
        out_log.write_text(json.dumps({"status": "failed", "error": err}, indent=2), encoding="utf-8")
        print(err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

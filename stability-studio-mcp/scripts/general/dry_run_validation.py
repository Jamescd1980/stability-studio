#!/usr/bin/env python3
"""CPU-only smoke checks for CI / pre-push (no ComfyUI required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.error_messages import humanize_error  # noqa: E402
from studio.hardware_profile import apply_video_safety_caps  # noqa: E402
from studio.scene_sequence import plan_scene_sequence  # noqa: E402
from studio.version_info import build_info  # noqa: E402


def main() -> int:
    errors: list[str] = []

    info = build_info()
    if not info.get("version"):
        errors.append("missing version")

    plan = plan_scene_sequence(
        script="1. hero stands\n2. hero bows\n3. hero smiles",
        hero_image="/tmp/hero.png",
    )
    if len(plan.get("steps", [])) != 3:
        errors.append("plan_scene_sequence beat count")

    _, _, loras, amp, nf, _, applied = apply_video_safety_caps(
        vram_gb=16,
        vram_free_gb=0.5,
        smooth_motion=True,
        lora_bundle="smooth_character",
        lora_ids=None,
        use_painter_i2v=True,
        workflow_id="i2v_5b_painter",
        num_frames=65,
        frame_rate=16,
        motion_amplitude=1.3,
    )
    if loras != "" and loras is not None:
        errors.append("expected lora_bundle cleared on 16GB")
    if nf > 33:
        errors.append("expected frame clamp under vram pressure")

    h = humanize_error("CUDA out of memory")
    if h.get("error_code") != "gpu_oom":
        errors.append("humanize_error oom pattern")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "version": info, "safety_sample": applied}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

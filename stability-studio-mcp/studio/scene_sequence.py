"""Plan multi-beat video/image sequences from short scripts (storyboard)."""

from __future__ import annotations

import re
from typing import Any

DEFAULT_CHAR = (
    "consistent character design, same outfit and face throughout, "
    "natural hands, anatomically correct, detailed face"
)

NEG_VIDEO = (
    "static, frozen, still image, blurry, deformed, bad anatomy, jittery, "
    "morphing face, different character, outfit change, hair color change, extra limbs"
)


def _parse_beats(script: str) -> list[str]:
    lines = [ln.strip() for ln in script.strip().splitlines() if ln.strip()]
    beats: list[str] = []
    for ln in lines:
        m = re.match(r"^(?:\d+[\).\:]|\-|\*)\s*(.+)$", ln)
        beats.append(m.group(1).strip() if m else ln)
    return beats or [script.strip()]


def plan_scene_sequence(
    *,
    script: str,
    food_group: str = "anime",
    hero_image: str = "",
    style: str = "",
    frames_per_beat: int = 49,
    frame_rate: float = 16.0,
    use_painter: bool = True,
    motion_amplitude: float = 1.15,
) -> dict[str, Any]:
    """Build a storyboard plan without touching the GPU."""
    beats = _parse_beats(script)
    resolved_style = style or {"anime": "ilustmix", "fantasy": "merged_dreams", "cyberpunk": "n4mik4", "photoreal": "juggernaut"}.get(
        food_group, "ilustmix"
    )
    steps: list[dict[str, Any]] = []
    chain_from_hero = bool(hero_image)

    for i, beat in enumerate(beats):
        prompt = f"{beat}, {DEFAULT_CHAR}"
        if i == 0 and not hero_image:
            steps.append(
                {
                    "index": i,
                    "kind": "t2i",
                    "tool": "generate_image",
                    "prompt": prompt,
                    "style": resolved_style,
                    "note": "Hero still — pass saved path as hero_image for execute",
                }
            )
            continue

        if i == 0 and chain_from_hero:
            steps.append(
                {
                    "index": i,
                    "kind": "i2v",
                    "tool": "generate_video",
                    "mode": "i2v",
                    "workflow_id": "i2v_5b_painter" if use_painter else "i2v_5b",
                    "image_path": hero_image,
                    "prompt": prompt,
                    "style": resolved_style,
                    "negative_prompt": NEG_VIDEO,
                    "num_frames": frames_per_beat,
                    "frame_rate": frame_rate,
                    "motion_amplitude": motion_amplitude if use_painter else None,
                    "smooth_motion": False,
                }
            )
            continue

        steps.append(
            {
                "index": i,
                "kind": "v2v",
                "tool": "generate_video",
                "mode": "v2v",
                "workflow_id": "v2v_5b_painter" if use_painter else "v2v_5b",
                "video_path": f"<output of beat {i - 1}>",
                "prompt": prompt,
                "style": resolved_style,
                "negative_prompt": NEG_VIDEO,
                "num_frames": frames_per_beat,
                "frame_rate": frame_rate,
                "motion_amplitude": motion_amplitude if use_painter else None,
                "smooth_motion": False,
                "concat_source": True,
            }
        )

    return {
        "food_group": food_group,
        "style": resolved_style,
        "beats": len(beats),
        "frames_per_beat": frames_per_beat,
        "estimated_duration_sec": round(len(beats) * frames_per_beat / frame_rate, 1),
        "steps": steps,
        "execute_hint": "Call generate_scene_sequence(execute=true) or run beats sequentially; "
        "chain v2v with concat_source=true for continuity.",
    }

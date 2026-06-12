"""Storyboard planning, readiness checks, and manifest helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from studio.scene_sequence import NEG_VIDEO, plan_scene_sequence


def _parse_storyboard_script(script: str) -> list[dict[str, str]]:
    """Parse beats: 'action | dialogue' or action-only lines."""
    beats: list[dict[str, str]] = []
    for raw in script.strip().splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^(?:\d+[\).\:]|\-|\*)\s*", "", line)
        if "|" in line:
            action, dialogue = [p.strip() for p in line.split("|", 1)]
        else:
            action, dialogue = line, ""
        beats.append({"action": action, "dialogue": dialogue})
    return beats


def plan_storyboard_scene(
    *,
    script: str,
    hero_image: str = "",
    food_group: str = "anime",
    style: str = "",
    voice_instruction: str = "",
    project_name: str = "",
    frames_per_beat: int = 49,
    resolution: str = "832x480",
    frame_rate: float = 16.0,
    motion_amplitude: float = 1.1,
    include_lipsync: bool = False,
    include_audio_mux: bool = False,
    splice_clips: bool = True,
    fade_last_beat: bool = False,
) -> dict[str, Any]:
    """
    High-level storyboard plan: hero I2V chain + optional MOSS + Infinitetalk + splice.

    Script format (one beat per line):
        walk toward camera | Greetings.
        polite bow | My name is Rin, you killed my father.
        lunge toward camera | Now prepare to die.
    """
    beats = _parse_storyboard_script(script)
    action_script = "\n".join(b["action"] for b in beats)
    base = plan_scene_sequence(
        script=action_script,
        food_group=food_group,
        hero_image=hero_image,
        style=style,
        frames_per_beat=frames_per_beat,
        frame_rate=frame_rate,
        use_painter=False,
        motion_amplitude=motion_amplitude,
    )
    # Replace draft ComfyUI steps with hero Wan2GP chain (validated Rin path).
    hero_steps: list[dict[str, Any]] = []
    chain_image = hero_image
    for i, beat in enumerate(beats):
        step: dict[str, Any] = {
            "index": i,
            "beat": beat,
            "hero_i2v": {
                "tool": "generate_video_hero",
                "image_path": chain_image or "<hero still from generate_image or source/>",
                "prompt": f"{beat['action']}, consistent character, same outfit and face, cinematic",
                "negative_prompt": NEG_VIDEO,
                "video_length": frames_per_beat,
                "resolution": resolution,
                "motion_amplitude": motion_amplitude,
            },
            "chain_frame_out": f"images/chain/beat{i}_last_frame.png",
        }
        if beat["dialogue"]:
            step["moss_audio"] = {
                "tool": "generate_audio",
                "mode": "voice_design",
                "text": beat["dialogue"],
                "instruction": voice_instruction or "young adult female, soft polite tone, close-mic",
                "deliver_to": "audio/",
            }
            if include_lipsync:
                step["infinitetalk"] = {
                    "tool": "wan2gp_infinitetalk",
                    "note": "VRAM-heavy ~25–60 min/clip on 16 GB; optional",
                    "image_refs_required": True,
                    "max_recommended_audio_s": 4.5,
                }
        hero_steps.append(step)
        chain_image = f"<extract last frame from beat {i} clip>"

    post: list[dict[str, str]] = []
    if splice_clips:
        post.append(
            {
                "step": "splice_hero_clips",
                "tool": "ffmpeg frame-accurate",
                "note": "Drop duplicate chain frames: clip[n][:-1] + clip[n+1][1:]",
                "output": "final/storyboard_spliced.mp4",
            }
        )
    if fade_last_beat:
        post.append({"step": "fade_last_beat", "output": "clips/beat_last_fade.mp4"})
    if include_audio_mux:
        post.append(
            {
                "step": "mux_audio",
                "note": "Prefer hero splice without lipsync on ≤16 GB; mux SFX under dialogue separately",
            }
        )

    return {
        "project_name": project_name,
        "food_group": food_group,
        "style": base["style"],
        "beats": len(beats),
        "parsed_beats": beats,
        "estimated_hero_duration_sec": round(len(beats) * frames_per_beat / frame_rate, 1),
        "hero_steps": hero_steps,
        "post_steps": post,
        "project_layout": {
            "temp": "raw Wan2GP / MOSS until approved",
            "images": "hero stills",
            "images/chain": "I2V handoff frames",
            "assets": "canny / lineart / openpose only",
            "clips": "approved hero MP4s",
            "audio": "dialogue + SFX",
            "logs": "JSON only",
            "final": "spliced deliverable",
        },
        "gpu_order_16gb": [
            "1. check_storyboard_readiness",
            "2. generate_image or place hero in images/",
            "3. check_gpu_backend → generate_video_hero per beat (Wan2GP only)",
            "4. Stop Wan2GP; check_gpu_backend → generate_audio per dialogue line (ComfyUI)",
            "5. Optional Infinitetalk: Wan2GP only, one clip at a time",
            "6. ffmpeg splice to final/ (no GPU)",
        ],
        "validated_example": "Rin kitsune — logs/rin_session_handoff.json, STORYBOARD-QUICKSTART.md",
        "execute_note": "plan-only today; run beats via generate_video_hero + project scripts or future execute=true",
        "draft_comfyui_plan": base,
    }


def check_storyboard_readiness(cfg: dict[str, Any]) -> dict[str, Any]:
    """Aggregate checks for a full storyboard pipeline on this machine."""
    from studio.gpu_backend import inspect_gpu_backend
    from studio.moss_assets import check_moss_assets
    from studio.output_paths import delivery_dir, delivery_temp_dir
    from studio.project_layout import ensure_project_layout, project_paths
    from studio.wan2gp_runner import check_wan2gp_runtime

    gpu = inspect_gpu_backend(cfg)
    wan2gp = check_wan2gp_runtime(cfg)
    moss = check_moss_assets(cfg)
    delivery = delivery_dir(cfg)
    temp = delivery_temp_dir(cfg)
    layout = ensure_project_layout(cfg)
    paths = project_paths(cfg)

    blocks: list[str] = []
    if not wan2gp.get("ready_for_hero"):
        blocks.append("Wan2GP Lightning v2 I2V assets or MCP not ready for hero clips")
    moss_sum = moss.get("summary") or {}
    if not (moss_sum.get("voice_design") and moss_sum.get("sound_effect")):
        blocks.append("MOSS-TTS assets or nodes missing for dialogue/SFX")
    if gpu.get("blocks"):
        blocks.append(f"GPU policy: {gpu['blocks'][0].get('reason', 'blocked')}")
    if delivery is None:
        blocks.append("outputs.delivery not set — configure project root in config.yaml")

    return {
        "ready": len(blocks) == 0,
        "blocks": blocks,
        "gpu_backend": gpu,
        "wan2gp": {
            "ready_for_hero": wan2gp.get("ready_for_hero"),
            "mcp_url": wan2gp.get("mcp_url"),
        },
        "moss": moss.get("summary"),
        "delivery": str(delivery) if delivery else None,
        "temp": str(temp) if temp else None,
        "project_layout": {k: str(v) for k, v in paths.items()} if paths else None,
        "infinitetalk_notes": {
            "vram": "Dedicated Wan2GP session; do not run ComfyUI concurrently on 16 GB",
            "duration": "Keep dialogue chunks ≤4.5 s; lip sync quality drops on longer audio",
            "image_refs": "Infinitetalk requires image_refs in settings (see Rin clip logs)",
            "fallback": "Use hero splice without lipsync when VRAM or time constrained",
        },
    }


def build_storyboard_manifest(
    *,
    title: str,
    project_root: str,
    beats: list[dict[str, Any]],
    final_deliverable: str = "",
    zip_archive: str = "",
    status: str = "complete",
) -> dict[str, Any]:
    """Canonical manifest for a finished or in-progress storyboard sequence."""
    return {
        "manifest_version": 1,
        "title": title,
        "status": status,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_root": project_root,
        "zip_archive": zip_archive,
        "final_deliverable": final_deliverable,
        "beats": beats,
        "layout_spec": "logs/recommended_project_layout.json",
    }

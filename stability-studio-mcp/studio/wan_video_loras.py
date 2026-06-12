"""Optional Wan 2.2 video LoRAs (motion, face, lighting, camera) — separate from base WORKFLOW_ASSETS."""

from __future__ import annotations

from typing import Any

from studio.wan_assets import FOLDER_MAP, _find_file, download_asset, model_dirs

HF_REPO = "wangkanai/wan22-fp16-i2v-loras"

# Curated I2V-friendly LoRAs (fp16, Wan 2.2). Download into Stability Matrix Lora/.
WAN_VIDEO_LORAS: dict[str, dict[str, Any]] = {
    "face_naturalizer": {
        "id": "face_naturalizer",
        "filename": "wan22-face-naturalizer.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-face-naturalizer.safetensors",
        "size_hint": "~586 MB",
        "default_weight": 0.65,
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter", "i2v"],
        "purpose": "Facial animation quality and more natural head motion (helps limb/face drift).",
    },
    "light_volumetric": {
        "id": "light_volumetric",
        "filename": "wan22-light-volumetric.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-light-volumetric.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.5,
        "workflows": ["i2v_5b", "i2v_5b_painter", "i2v", "t2v"],
        "purpose": "Volumetric god-rays / cinematic church lighting.",
    },
    "camera_steady": {
        "id": "camera_steady",
        "filename": "wan22-camera-rotation-rank16-v2.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-camera-rotation-rank16-v2.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.35,
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
        "purpose": "Controlled orbit/rotation — use low weight for steady aisle dolly.",
    },
    "camera_arc": {
        "id": "camera_arc",
        "filename": "wan22-camera-arcshot-rank16-v2-high.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-camera-arcshot-rank16-v2-high.safetensors",
        "size_hint": "~293 MB",
        "default_weight": 0.4,
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
        "purpose": "Cinematic arc shot around subject.",
    },
    "action_wink": {
        "id": "action_wink",
        "filename": "wan22-action-wink-i2v-v1-low.safetensors",
        "folder": "loras",
        "repo": HF_REPO,
        "path": "loras/wan/wan22-action-wink-i2v-v1-low.safetensors",
        "size_hint": "~147 MB",
        "default_weight": 0.55,
        "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
        "purpose": "Small gesture motion reference (not for walk cycles).",
    },
}

# Suggested bundles for agents / docs.
WAN_VIDEO_LORA_BUNDLES: dict[str, list[str]] = {
    "walk_cycle": ["face_naturalizer"],
    "smooth_character": ["face_naturalizer", "camera_steady"],
    "cinematic_church": ["face_naturalizer", "light_volumetric"],
    "motion_boost": ["face_naturalizer", "light_volumetric", "camera_steady"],
}

# Optional machine-local LoRAs (gitignored). Copy wan_video_loras_local.example.py → wan_video_loras_local.py
try:
    from studio.wan_video_loras_local import (  # type: ignore[import-not-found]
        LOCAL_WAN_VIDEO_LORA_BUNDLES,
        LOCAL_WAN_VIDEO_LORAS,
    )

    WAN_VIDEO_LORAS.update(LOCAL_WAN_VIDEO_LORAS)
    WAN_VIDEO_LORA_BUNDLES.update(LOCAL_WAN_VIDEO_LORA_BUNDLES)
except ImportError:
    pass

# Tuned defaults when generate_video(smooth_motion=true).
SMOOTH_MOTION_DEFAULTS: dict[str, Any] = {
    "motion_amplitude": 1.08,
    "frame_rate": 12.0,
    "sampler_steps": 28,
    "sampler_cfg": 5.0,
    "lora_bundle": "smooth_character",
    "extra_negative": "jittery, morphing, flickering, strobe, fast erratic motion, warping",
}


def apply_smooth_motion_preset(
    *,
    smooth_motion: bool,
    motion_amplitude: float,
    frame_rate: float | None,
    lora_bundle: str,
    lora_ids: list[str] | None,
    vram_gb: float | None = None,
) -> tuple[float, float | None, str, list[str] | None, dict[str, Any]]:
    """Return tuned motion/fps/lora settings for smoother Wan I2V/V2V."""
    applied: dict[str, Any] = {}
    if not smooth_motion:
        return motion_amplitude, frame_rate, lora_bundle, lora_ids, applied

    defaults = SMOOTH_MOTION_DEFAULTS
    if motion_amplitude >= 1.12:
        motion_amplitude = float(defaults["motion_amplitude"])
        applied["motion_amplitude"] = motion_amplitude
    if frame_rate is None:
        frame_rate = float(defaults["frame_rate"])
        applied["frame_rate"] = frame_rate
    # Dual Wan video LoRAs (~900 MB loaded) can OOM with PainterI2V on 16 GB GPUs.
    if not lora_bundle and not lora_ids:
        if vram_gb is not None and vram_gb <= 16:
            applied["lora_bundle_skipped"] = (
                f"{vram_gb:.0f}GB VRAM — using PainterI2V only (no Wan video LoRAs)"
            )
        else:
            lora_bundle = str(defaults["lora_bundle"])
            applied["lora_bundle"] = lora_bundle
    applied["sampler_steps"] = defaults["sampler_steps"]
    applied["sampler_cfg"] = defaults["sampler_cfg"]
    applied["extra_negative"] = defaults["extra_negative"]
    return motion_amplitude, frame_rate, lora_bundle, lora_ids, applied


def resolve_lora_entry(lora_id: str) -> dict[str, Any]:
    key = lora_id.strip().lower()
    if key in WAN_VIDEO_LORAS:
        return WAN_VIDEO_LORAS[key]
    for entry in WAN_VIDEO_LORAS.values():
        if entry["filename"].lower() == key or entry["filename"].lower() == f"{key}.safetensors":
            return entry
    raise KeyError(f"Unknown Wan video LoRA id: {lora_id!r}. Known: {list(WAN_VIDEO_LORAS)}")


def resolve_lora_list(
    lora_ids: list[str] | None = None,
    *,
    bundle: str = "",
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return [{file, weight, id}, ...] for workflow injection."""
    ids: list[str] = []
    if bundle:
        ids.extend(WAN_VIDEO_LORA_BUNDLES.get(bundle.strip().lower(), []))
    if lora_ids:
        ids.extend(lora_ids)
    if not ids:
        return []

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in ids:
        entry = resolve_lora_entry(raw)
        lid = entry["id"]
        if lid in seen:
            continue
        seen.add(lid)
        w = (weights or {}).get(lid, entry.get("default_weight", 0.6))
        out.append({"id": lid, "file": entry["filename"], "weight": float(w)})
    return out


def check_wan_video_loras(cfg: dict[str, Any], lora_ids: list[str] | None = None) -> dict[str, Any]:
    dirs = model_dirs(cfg)
    lora_dir = dirs.get("loras")
    entries = (
        [resolve_lora_entry(i) for i in lora_ids]
        if lora_ids
        else list(WAN_VIDEO_LORAS.values())
    )
    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for entry in entries:
        found = _find_file(entry["filename"], dirs, "loras")
        item = {k: entry[k] for k in ("id", "filename", "purpose", "default_weight", "size_hint") if k in entry}
        if found:
            installed.append({**item, "path": str(found)})
        else:
            missing.append(item)
    return {
        "installed": installed,
        "missing": missing,
        "ready": len(missing) == 0,
        "bundles": WAN_VIDEO_LORA_BUNDLES,
        "catalog": {k: v.get("purpose", "") for k, v in WAN_VIDEO_LORAS.items()},
    }


def download_wan_video_loras(
    cfg: dict[str, Any],
    *,
    lora_ids: list[str] | None = None,
    bundle: str = "",
    force: bool = False,
) -> list[dict[str, Any]]:
    resolved = resolve_lora_list(lora_ids, bundle=bundle)
    if bundle and not resolved:
        raise ValueError(f"Unknown bundle: {bundle!r}. Known: {list(WAN_VIDEO_LORA_BUNDLES)}")
    if not resolved and lora_ids:
        resolved = resolve_lora_list(lora_ids)

    targets = resolved or [
        {"id": e["id"], "file": e["filename"], "weight": e.get("default_weight", 0.6)}
        for e in WAN_VIDEO_LORAS.values()
    ]
    results: list[dict[str, Any]] = []
    for item in targets:
        entry = resolve_lora_entry(item["id"])
        try:
            path = download_asset(cfg, entry, force=force)
            results.append({"id": entry["id"], "filename": entry["filename"], "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"id": entry["id"], "filename": entry["filename"], "ok": False, "error": str(exc)})
    return results

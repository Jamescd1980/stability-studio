"""MOSS-TTS model manifest, readiness checks, and Hugging Face downloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MOSS_NODE_PACKAGE = "comfyui-moss-tts"
MOSS_NODES = (
    "MossTTSModelLoader",
    "MossTTSGenerate",
    "MossTTSSoundEffect",
    "MossTTSVoiceDesign",
)

MOSS_MODELS: dict[str, dict[str, Any]] = {
    "audio_tokenizer": {
        "id": "audio_tokenizer",
        "repo_id": "OpenMOSS-Team/MOSS-Audio-Tokenizer",
        "dir_name": "MOSS-Audio-Tokenizer",
        "required_for": ["speech", "sound_effect", "voice_design"],
        "vram_hint": "shared codec",
        "purpose": "Shared audio codec — required by all MOSS models",
    },
    "tts_local": {
        "id": "tts_local",
        "repo_id": "OpenMOSS-Team/MOSS-TTS-Local-Transformer",
        "dir_name": "MOSS-TTS-Local-Transformer",
        "model_variant": "MOSS-TTS (Local 1.7B)",
        "mode": "speech",
        "vram_hint": "~5 GB",
        "purpose": "Fast text-to-speech without reference audio (recommended on 16 GB)",
    },
    "sound_effect": {
        "id": "sound_effect",
        "repo_id": "OpenMOSS-Team/MOSS-SoundEffect",
        "dir_name": "MOSS-SoundEffect",
        "model_variant": "MOSS-SoundEffect",
        "mode": "sound_effect",
        "vram_hint": "~18 GB",
        "purpose": "Text-to sound effects and ambience",
        "shard_glob": "model-*.safetensors",
        "min_shards": 4,
    },
    "voice_generator": {
        "id": "voice_generator",
        "repo_id": "OpenMOSS-Team/MOSS-VoiceGenerator",
        "dir_name": "MOSS-VoiceGenerator",
        "model_variant": "MOSS-VoiceGenerator",
        "mode": "voice_design",
        "vram_hint": "~18 GB",
        "purpose": "Voice design from text description (no reference clip)",
    },
}


def moss_models_dir(cfg: dict[str, Any]) -> Path:
    comfy = Path(cfg["stability_matrix"]["packages"]["comfyui"])
    return comfy / "models" / "moss-tts"


def moss_custom_node_dir(cfg: dict[str, Any]) -> Path:
    comfy = Path(cfg["stability_matrix"]["packages"]["comfyui"])
    return comfy / "custom_nodes" / MOSS_NODE_PACKAGE


def _model_ready(model_dir: Path, entry: dict[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not model_dir.is_dir():
        return False, [f"missing directory {model_dir.name}"]

    config = model_dir / "config.json"
    if not config.is_file():
        missing.append("config.json")

    shard_glob = entry.get("shard_glob")
    if shard_glob:
        shards = sorted(model_dir.glob(shard_glob))
        min_shards = int(entry.get("min_shards", 1))
        if len(shards) < min_shards:
            missing.append(f"{shard_glob} ({len(shards)}/{min_shards} shards)")
    else:
        index = model_dir / "model.safetensors.index.json"
        single = model_dir / "model.safetensors"
        shards = list(model_dir.glob("model-*.safetensors"))
        if not single.is_file() and not shards and not index.is_file():
            missing.append("model weights")

    return len(missing) == 0, missing


def check_moss_assets(cfg: dict[str, Any]) -> dict[str, Any]:
    root = moss_models_dir(cfg)
    node_dir = moss_custom_node_dir(cfg)
    models: dict[str, Any] = {}
    for key, entry in MOSS_MODELS.items():
        model_dir = root / entry["dir_name"]
        ready, missing = _model_ready(model_dir, entry)
        models[key] = {
            **entry,
            "path": str(model_dir),
            "ready": ready,
            "missing": missing,
        }
    speech_ready = models["audio_tokenizer"]["ready"] and models["tts_local"]["ready"]
    sfx_ready = models["audio_tokenizer"]["ready"] and models["sound_effect"]["ready"]
    voice_ready = models["audio_tokenizer"]["ready"] and models["voice_generator"]["ready"]
    return {
        "models_dir": str(root),
        "custom_node": str(node_dir),
        "custom_node_installed": node_dir.is_dir(),
        "models": models,
        "summary": {
            "speech": speech_ready,
            "sound_effect": sfx_ready,
            "voice_design": voice_ready,
        },
        "recommended": {
            "speech": "tts_local (MOSS-TTS Local 1.7B)",
            "sound_effect": "sound_effect after full 4-shard download",
            "voice_design": "voice_generator (optional; heavy)",
        },
    }


def download_moss_models(
    cfg: dict[str, Any],
    *,
    model_ids: list[str] | None = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    from huggingface_hub import snapshot_download

    root = moss_models_dir(cfg)
    root.mkdir(parents=True, exist_ok=True)
    keys = model_ids or list(MOSS_MODELS.keys())
    results: list[dict[str, Any]] = []

    for key in keys:
        entry = MOSS_MODELS.get(key)
        if not entry:
            results.append({"id": key, "status": "error", "error": "unknown model id"})
            continue
        target = root / entry["dir_name"]
        item: dict[str, Any] = {"id": key, "repo_id": entry["repo_id"], "path": str(target)}
        ready, _ = _model_ready(target, entry)
        if ready and not force:
            item["status"] = "skipped"
            results.append(item)
            continue
        try:
            path = snapshot_download(
                repo_id=entry["repo_id"],
                local_dir=str(target),
                local_dir_use_symlinks=False,
                force_download=force,
            )
            item["status"] = "ok"
            item["local_dir"] = path
        except Exception as exc:
            item["status"] = "error"
            item["error"] = str(exc)
        results.append(item)
    return results


def media_paths(cfg: dict[str, Any]) -> dict[str, str]:
    """Canonical local paths for images, audio, and video outputs."""
    from studio.output_paths import delivery_dir, delivery_temp_dir
    from studio.project_layout import project_paths

    sm = Path(cfg["stability_matrix"]["root"])
    data = Path(cfg["stability_matrix"]["data"])
    comfy = Path(cfg["stability_matrix"]["packages"]["comfyui"])
    mcp_root = Path(cfg.get("_root", Path(__file__).resolve().parents[1]))
    wan2gp = Path(cfg.get("wan2gp", {}).get("root") or (data / "Packages" / "Wan2GP"))
    delivery = delivery_dir(cfg)
    temp = delivery_temp_dir(cfg)
    paths = {
        "mcp_outputs": str(mcp_root / "outputs"),
        "comfyui_output": str(comfy / "output"),
        "comfyui_input": str(comfy / "input"),
        "comfyui_audio": str(comfy / "output" / "audio"),
        "wan2gp_outputs": str(temp or delivery or (wan2gp / "outputs")),
        "wan2gp_ckpts": str(wan2gp / "ckpts"),
        "moss_models": str(comfy / "models" / "moss-tts"),
        "stability_matrix_models": str(cfg["stability_matrix"]["models"]),
        "stability_matrix_workflows": str(cfg["stability_matrix"]["workflows"]),
    }
    if delivery is not None:
        paths["delivery"] = str(delivery)
        paths["moss_audio_delivery"] = str(temp or delivery)
        paths["wan2gp_video_delivery"] = str(temp or delivery)
    layout = project_paths(cfg)
    if layout is not None:
        for key, path in layout.items():
            paths[f"project_{key}"] = str(path)
    return paths

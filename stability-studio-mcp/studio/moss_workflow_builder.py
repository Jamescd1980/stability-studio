"""ComfyUI API workflows for MOSS-TTS audio generation."""

from __future__ import annotations

from typing import Any

from studio.audio_post import estimate_voice_max_tokens

MODEL_VARIANTS = {
    "speech": "MOSS-TTS (Local 1.7B)",
    "sound_effect": "MOSS-SoundEffect",
    "voice_design": "MOSS-VoiceGenerator",
}

LOCAL_1_7B_PARAMS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 50,
    "repetition_penalty": 1.1,
}

SFX_PARAMS = {
    "temperature": 1.5,
    "top_p": 0.6,
    "top_k": 50,
    "repetition_penalty": 1.2,
}

VOICE_DESIGN_PARAMS = {
    "temperature": 1.2,
    "top_p": 0.6,
    "top_k": 50,
    "repetition_penalty": 1.1,
}


def build_moss_speech_workflow(
    *,
    text: str,
    language: str = "en",
    seed: int = 0,
    filename_prefix: str = "audio/moss_tts",
) -> dict[str, Any]:
    p = LOCAL_1_7B_PARAMS
    return {
        "1": {
            "class_type": "MossTTSModelLoader",
            "inputs": {
                "model_variant": MODEL_VARIANTS["speech"],
                "local_model_path": "",
                "codec_local_path": "",
            },
        },
        "2": {
            "class_type": "MossTTSGenerate",
            "inputs": {
                "moss_pipe": ["1", 0],
                "language": language if language in {"auto", "zh", "en", "ja", "ko"} else "en",
                "text": text,
                "seed": seed,
                "temperature": p["temperature"],
                "top_p": p["top_p"],
                "top_k": p["top_k"],
                "repetition_penalty": p["repetition_penalty"],
                "max_new_tokens": 4096,
                "enable_duration_control": False,
                "duration_tokens": 325,
                "head_handle": 0.0,
                "tail_handle": 0.0,
            },
        },
        "3": _save_audio_node("2", filename_prefix),
    }


def build_moss_sound_effect_workflow(
    *,
    prompt: str,
    duration_seconds: float = 5.0,
    seed: int = 0,
    filename_prefix: str = "audio/moss_sfx",
) -> dict[str, Any]:
    p = SFX_PARAMS
    return {
        "1": {
            "class_type": "MossTTSModelLoader",
            "inputs": {
                "model_variant": MODEL_VARIANTS["sound_effect"],
                "local_model_path": "",
                "codec_local_path": "",
            },
        },
        "2": {
            "class_type": "MossTTSSoundEffect",
            "inputs": {
                "moss_pipe": ["1", 0],
                "ambient_sound": prompt,
                "duration_seconds": max(0.5, min(float(duration_seconds), 60.0)),
                "seed": seed,
                "temperature": p["temperature"],
                "top_p": p["top_p"],
                "top_k": p["top_k"],
                "repetition_penalty": p["repetition_penalty"],
                "max_new_tokens": 4096,
                "head_handle": 0.0,
                "tail_handle": 0.0,
            },
        },
        "3": _save_audio_node("2", filename_prefix),
    }


def build_moss_voice_design_workflow(
    *,
    text: str,
    instruction: str,
    language: str = "en",
    seed: int = 0,
    filename_prefix: str = "audio/moss_voice",
    max_new_tokens: int | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    p = VOICE_DESIGN_PARAMS
    token_cap = max_new_tokens if max_new_tokens is not None else estimate_voice_max_tokens(
        text, duration_seconds=duration_seconds
    )
    use_duration = duration_seconds is not None
    duration_value = float(duration_seconds) if use_duration else 3.5
    return {
        "1": {
            "class_type": "MossTTSModelLoader",
            "inputs": {
                "model_variant": MODEL_VARIANTS["voice_design"],
                "local_model_path": "",
                "codec_local_path": "",
            },
        },
        "2": {
            "class_type": "MossTTSVoiceDesign",
            "inputs": {
                "moss_pipe": ["1", 0],
                "language": language if language in {"auto", "zh", "en", "ja", "ko"} else "en",
                "text": text,
                "instruction": instruction,
                "seed": seed,
                "temperature": p["temperature"],
                "top_p": p["top_p"],
                "top_k": p["top_k"],
                "repetition_penalty": p["repetition_penalty"],
                "max_new_tokens": token_cap,
                "enable_duration_control": use_duration,
                "duration_seconds": duration_value,
                "head_handle": 0.0,
                "tail_handle": 0.0,
            },
        },
        "3": _save_audio_node("2", filename_prefix),
    }


def _save_audio_node(source_id: str, filename_prefix: str) -> dict[str, Any]:
    return {
        "class_type": "SaveAudioMP3",
        "inputs": {
            "audio": [source_id, 0],
            "filename_prefix": filename_prefix,
            "quality": "320k",
        },
    }

"""CreateBrain / nari-prompt Ollama VRAM policy on GenerationHost (RTX 5090).

CreateBrain may load on the 5090 for snappy OI chat while Comfy stills are light.
Before Wan / heavy video / MOSS audio on the same GPU: unload her so diffusion
keeps the full card (peaks ~26–27 GB on 32 GB).
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import requests


def _nari_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "enabled": True,
        "url": "",  # empty → derive from comfyui host :11434
        "models": ["nari", "nari-prompt"],
        "unload_before_video": True,
        "unload_before_audio": True,
        "unload_before_hero": True,
        "timeout_sec": 8.0,
    }
    merged = dict(defaults)
    merged.update(cfg.get("nari_ollama") or {})
    return merged


def ollama_base_url(cfg: dict[str, Any]) -> str:
    n = _nari_cfg(cfg)
    if n.get("url"):
        return str(n["url"]).rstrip("/")
    raw = str((cfg.get("comfyui") or {}).get("url") or "http://127.0.0.1:8188")
    parsed = urlparse(raw)
    host = parsed.hostname or "127.0.0.1"
    return f"http://{host}:11434"


def nari_ollama_status(cfg: dict[str, Any]) -> dict[str, Any]:
    """What's loaded in GenerationHost Ollama (for check_gpu_backend / agents)."""
    base = ollama_base_url(cfg)
    out: dict[str, Any] = {
        "ok": True,
        "url": base,
        "policy": (
            "CreateBrain may use the 5090 while Comfy stills are light. "
            "MCP unloads nari/nari-prompt before Wan video / hero / MOSS audio."
        ),
        "models": [],
    }
    try:
        r = requests.get(f"{base}/api/ps", timeout=float(_nari_cfg(cfg).get("timeout_sec") or 8))
        r.raise_for_status()
        data = r.json() if r.content else {}
        models = data.get("models") or []
        out["models"] = models
        names = []
        for m in models:
            if isinstance(m, dict):
                names.append(str(m.get("name") or m.get("model") or ""))
        out["nari_loaded"] = any(n.startswith("nari") for n in names)
        out["processor_hint"] = [
            {
                "name": m.get("name") or m.get("model"),
                "size": m.get("size"),
                "details": m.get("details"),
            }
            for m in models
            if isinstance(m, dict)
        ]
    except requests.RequestException as exc:
        out["ok"] = False
        out["error"] = str(exc)
        out["nari_loaded"] = None
    return out


def unload_nari_models(
    cfg: dict[str, Any],
    *,
    reason: str = "",
    models: list[str] | None = None,
) -> dict[str, Any]:
    """Unload CreateBrain tags so Wan/audio can claim the 5090. Safe no-op if already idle."""
    ncfg = _nari_cfg(cfg)
    if not ncfg.get("enabled", True):
        return {"ok": True, "skipped": True, "reason": "nari_ollama.enabled=false"}
    base = ollama_base_url(cfg)
    tags = list(models or ncfg.get("models") or ["nari", "nari-prompt"])
    timeout = float(ncfg.get("timeout_sec") or 8)
    results: list[dict[str, Any]] = []
    for tag in tags:
        tag = str(tag).strip()
        if not tag:
            continue
        # Prefer keep_alive=0 (works over LAN). Fall back to /api/chat unload pattern.
        try:
            r = requests.post(
                f"{base}/api/generate",
                json={"model": tag, "keep_alive": 0, "prompt": ""},
                timeout=timeout,
            )
            # Some builds want /api/chat with keep_alive
            if r.status_code >= 400:
                r = requests.post(
                    f"{base}/api/chat",
                    json={
                        "model": tag,
                        "messages": [],
                        "keep_alive": 0,
                    },
                    timeout=timeout,
                )
            results.append(
                {
                    "model": tag,
                    "status_code": r.status_code,
                    "ok": r.ok or r.status_code in {404, 200},
                }
            )
        except requests.RequestException as exc:
            results.append({"model": tag, "ok": False, "error": str(exc)})
    return {
        "ok": all(x.get("ok") for x in results) if results else True,
        "reason": reason or "vram_for_diffusion",
        "unloaded": results,
        "after": nari_ollama_status(cfg),
    }


def maybe_unload_nari_for_video(cfg: dict[str, Any], *, workflow_id: str = "", mode: str = "") -> dict[str, Any]:
    if not _nari_cfg(cfg).get("unload_before_video", True):
        return {"ok": True, "skipped": True}
    return unload_nari_models(
        cfg,
        reason=f"before_video mode={mode or '?'} workflow_id={workflow_id or 'auto'}",
    )


def maybe_unload_nari_for_audio(cfg: dict[str, Any]) -> dict[str, Any]:
    if not _nari_cfg(cfg).get("unload_before_audio", True):
        return {"ok": True, "skipped": True}
    return unload_nari_models(cfg, reason="before_moss_audio")


def maybe_unload_nari_for_hero(cfg: dict[str, Any]) -> dict[str, Any]:
    if not _nari_cfg(cfg).get("unload_before_hero", True):
        return {"ok": True, "skipped": True}
    return unload_nari_models(cfg, reason="before_wan2gp_hero")

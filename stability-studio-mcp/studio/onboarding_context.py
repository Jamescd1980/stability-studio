"""Load onboarding pack for get_onboarding_context MCP tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ONBOARDING_ROOT = Path(__file__).resolve().parents[2] / "onboarding"


def _load_checklist() -> dict[str, Any]:
    path = ONBOARDING_ROOT / "CHECKLIST.yaml"
    if not path.is_file():
        return {"error": f"missing {path}"}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def vram_tier_label(vram_gb: float) -> str:
    if vram_gb >= 24:
        return "gte_24_gb"
    if vram_gb > 16:
        return "16_to_23_gb"
    return "lte_16_gb"


def onboarding_for_vram(vram_gb: float, checklist: dict[str, Any]) -> dict[str, Any]:
    routing = (checklist.get("vram_routing") or {}).get(vram_tier_label(vram_gb), {})
    return {
        "detected_vram_gb": vram_gb,
        "tier_key": vram_tier_label(vram_gb),
        **routing,
    }


def build_onboarding_context(
    cfg: dict[str, Any],
    *,
    hardware: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge checklist with live hardware when available."""
    checklist = _load_checklist()
    hw = hardware or {}
    vram = float(hw.get("vram_gb") or hw.get("detected_vram_gb") or 0)

    vram_advice = onboarding_for_vram(vram, checklist) if vram > 0 else {
        "note": "Launch ComfyUI and call get_generation_context to detect VRAM",
        "tier_key": "unknown",
    }

    return {
        "pack_root": str(ONBOARDING_ROOT),
        "disclaimer": checklist.get("disclaimer", "").strip(),
        "studio_version": checklist.get("studio_version"),
        "agent_playbook": "onboarding/ONBOARDING.md",
        "checklist_file": "onboarding/CHECKLIST.yaml",
        "troubleshooting": "onboarding/TROUBLESHOOTING.md",
        "project_template": "onboarding/PROJECT.template/",
        "example_reference": "onboarding/examples/rin/README.md",
        "discovery_questions": checklist.get("discovery_questions"),
        "required_programs": checklist.get("required_programs"),
        "tiers": checklist.get("tiers"),
        "install_sequence": checklist.get("install_sequence"),
        "first_win": checklist.get("first_win"),
        "vram_advice": vram_advice,
        "wan2gp_policy": (
            "Do not offer Wan2GP on ≥24 GB — use ComfyUI only. "
            "On ≤16 GB, offer Wan2GP only when user explicitly wants hero motion or lip sync."
        ),
        "delivery_configured": bool((cfg.get("outputs") or {}).get("delivery")),
        "config_template": "onboarding/config.yaml.template",
    }

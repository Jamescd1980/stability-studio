"""Standard delivery-project folder layout (images, assets, temp, logs, …)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_SUBDIRS = (
    "source",
    "images",
    "images/chain",
    "assets",
    "clips",
    "audio",
    "temp",
    "logs",
    "final",
    "rejected",
)


def layout_subdirs(cfg: dict[str, Any]) -> dict[str, str]:
    """Relative subfolder names under outputs.delivery (override via outputs.layout)."""
    custom = (cfg.get("outputs") or {}).get("layout") or {}
    base = {
        "source": "source",
        "images": "images",
        "chain": "images/chain",
        "assets": "assets",
        "clips": "clips",
        "audio": "audio",
        "temp": "temp",
        "logs": "logs",
        "final": "final",
        "rejected": "rejected",
    }
    base.update({k: str(v) for k, v in custom.items() if v})
    return base


def project_root(cfg: dict[str, Any]) -> Path | None:
    raw = (cfg.get("outputs") or {}).get("delivery")
    if not raw:
        return None
    return Path(raw)


def project_paths(cfg: dict[str, Any]) -> dict[str, Path] | None:
    """Resolved paths for a configured delivery project."""
    root = project_root(cfg)
    if root is None:
        return None
    subs = layout_subdirs(cfg)
    return {key: root / rel for key, rel in subs.items()}


def ensure_project_layout(cfg: dict[str, Any]) -> dict[str, Path] | None:
    paths = project_paths(cfg)
    if paths is None:
        return None
    for rel in DEFAULT_SUBDIRS:
        (paths["source"].parent / rel).mkdir(parents=True, exist_ok=True)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths

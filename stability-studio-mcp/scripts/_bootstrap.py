"""Shared bootstrap for CLI scripts under scripts/."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def setup_path() -> Path:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return ROOT


def load_engine() -> tuple[dict[str, Any], Any, Any]:
    setup_path()
    from studio.catalog import StyleCatalog
    from studio.config import catalog_path, load_config
    from studio.engine import GenerationEngine

    cfg = load_config()
    catalog = StyleCatalog(catalog_path(cfg), cfg)
    return cfg, catalog, GenerationEngine(cfg, catalog)


def default_delivery_dir() -> Path:
    """Project delivery folder from config, else MCP outputs/."""
    cfg, _, _ = load_engine()
    delivery = (cfg.get("outputs") or {}).get("delivery")
    if delivery:
        return Path(delivery)
    return ROOT / "outputs"

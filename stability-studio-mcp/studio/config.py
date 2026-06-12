from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict[str, Any]:
    path = ROOT / "config.yaml"
    if not path.exists():
        example = ROOT / "config.yaml.example"
        if example.exists():
            raise FileNotFoundError(
                f"Missing {path.name}. Copy config.yaml.example to config.yaml and edit paths."
            )
        raise FileNotFoundError(f"Missing {path.name}. See config.yaml.example.")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["_root"] = str(ROOT)
    data["_package_root"] = str(ROOT)
    return data


def catalog_path(cfg: dict[str, Any]) -> Path:
    rel = cfg.get("catalog_file", "catalog.yaml")
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_cm_info(model_path: Path) -> dict[str, Any] | None:
    info_path = model_path.with_suffix(model_path.suffix + ".cm-info.json")
    if not info_path.exists():
        stem = model_path.stem
        alt = model_path.parent / f"{stem}.cm-info.json"
        if alt.exists():
            info_path = alt
        else:
            return None
    try:
        with info_path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def scan_checkpoints(models_dir: Path) -> list[dict[str, Any]]:
    checkpoint_dir = models_dir / "StableDiffusion"
    if not checkpoint_dir.exists():
        return []

    results: list[dict[str, Any]] = []
    for path in sorted(checkpoint_dir.glob("*.safetensors")):
        info = _read_cm_info(path) or {}
        tags = [t.lower() for t in info.get("Tags", [])]
        name = info.get("ModelName") or path.stem
        results.append(
            {
                "file": path.name,
                "path": str(path),
                "name": name,
                "tags": tags,
                "base_model": info.get("BaseModel"),
                "trained_words": info.get("TrainedWords", []),
                "nsfw": info.get("Nsfw", False),
            }
        )
    return results


def scan_loras(models_dir: Path, extra_paths: list[str] | None = None) -> list[dict[str, Any]]:
    loras: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_from_dir(directory: Path, source: str) -> None:
        if not directory.exists():
            return
        for path in directory.rglob("*"):
            if path.suffix.lower() not in {".safetensors", ".pt"}:
                continue
            if path.name in seen:
                continue
            seen.add(path.name)
            info = _read_cm_info(path) or {}
            tags = [t.lower() for t in info.get("Tags", [])]
            loras.append(
                {
                    "file": path.name,
                    "path": str(path),
                    "name": info.get("ModelName") or path.stem,
                    "tags": tags,
                    "trained_words": info.get("TrainedWords", []),
                    "source": source,
                }
            )

    add_from_dir(models_dir / "Lora", "stability_matrix")
    add_from_dir(models_dir / "LyCORIS", "stability_matrix")
    for extra in extra_paths or []:
        add_from_dir(Path(extra), Path(extra).name)

    return sorted(loras, key=lambda x: x["file"].lower())


def scan_video_workflows(workflows_dir: Path) -> list[dict[str, Any]]:
    if not workflows_dir.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(workflows_dir.glob("*.json")):
        kind = "unknown"
        lower = path.name.lower()
        if "t2v" in lower or "text-to-video" in lower:
            kind = "t2v"
        elif "i2v" in lower or "image-2-video" in lower or "img2vid" in lower:
            kind = "i2v"
        items.append({"file": path.name, "path": str(path), "mode": kind})
    return items


def suggest_styles_from_models(checkpoints: list[dict[str, Any]]) -> dict[str, str]:
    """Map style keywords to checkpoint filenames based on tags/names."""
    suggestions: dict[str, str] = {}
    for ckpt in checkpoints:
        tags = set(ckpt.get("tags", []))
        name = (ckpt.get("name") or "").lower()
        fname = ckpt["file"].lower()
        if "juggernaut" in fname:
            suggestions.setdefault("juggernaut", ckpt["file"])
        if "abyssorangemix" in fname.replace("_", ""):
            suggestions.setdefault("aom2", ckpt["file"])
        if "realisian" in fname:
            suggestions.setdefault("realisian", ckpt["file"])
        if "illustrious" in name or "illustrious" in fname:
            suggestions.setdefault("anime", ckpt["file"])
        elif "anime" in tags or "ilustmix" in fname:
            suggestions.setdefault("ilustmix", ckpt["file"])
        if "photorealistic" in tags or "cyberrealistic" in fname:
            suggestions.setdefault("juggernaut", ckpt["file"])
        if "prefectpony" in fname.replace("_", ""):
            suggestions.setdefault("prefect_pony", ckpt["file"])
        if "ponydiffusionv6" in fname.replace("_", ""):
            suggestions.setdefault("pony", ckpt["file"])
        if "divineelegance" in fname.replace(" ", "").lower():
            suggestions.setdefault("merged_dreams", ckpt["file"])
    return suggestions

"""Download checkpoint files from Civitai (requires API key for most models)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests

CIVITAI_DOWNLOAD = "https://civitai.com/api/download/models/{version_id}"


def civitai_api_key(cfg: dict[str, Any]) -> str:
    key = (cfg.get("civitai") or {}).get("api_key") or ""
    if not key:
        key = os.environ.get("CIVITAI_API_TOKEN") or os.environ.get("CIVITAI_API_KEY") or ""
    return str(key).strip()


def download_civitai_checkpoint(
    *,
    version_id: str | int,
    dest: Path,
    api_key: str,
    force: bool = False,
    timeout: int = 7200,
) -> Path:
    """Stream a Civitai model version to dest. version_id is Civitai modelVersions id."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and not force:
        return dest
    if not api_key:
        raise ValueError(
            "Civitai API key required. Set civitai.api_key in config.yaml or "
            "CIVITAI_API_TOKEN env var. Create at https://civitai.com/user/account"
        )

    url = CIVITAI_DOWNLOAD.format(version_id=version_id)
    headers = {"Authorization": f"Bearer {api_key}"}
    tmp = dest.with_suffix(dest.suffix + ".part")

    with requests.get(url, headers=headers, stream=True, timeout=60, allow_redirects=True) as r:
        if r.status_code == 401:
            raise PermissionError("Civitai rejected the API key (401). Check civitai.api_key in config.yaml.")
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    done += len(chunk)
                    if total and done % (100 * 1024 * 1024) < len(chunk):
                        print(f"  ... {done // (1024 * 1024)} / {total // (1024 * 1024)} MB")

    tmp.replace(dest)
    return dest


def download_style_checkpoint(cfg: dict[str, Any], style: dict[str, Any], *, force: bool = False) -> Path:
    """Download checkpoint for a catalog style with a download: block."""
    dl = style.get("download") or {}
    if dl.get("source") != "civitai":
        raise ValueError("No Civitai download metadata on this style")

    filename = style.get("checkpoint") or dl.get("filename")
    if not filename:
        raise ValueError("No checkpoint filename configured")

    models = Path(cfg.get("stability_matrix", {}).get("models", ""))
    dest = models / "StableDiffusion" / filename
    version_id = dl.get("civitai_version_id")
    if not version_id:
        raise ValueError("download.civitai_version_id missing in catalog")

    return download_civitai_checkpoint(
        version_id=version_id,
        dest=dest,
        api_key=civitai_api_key(cfg),
        force=force,
    )


def download_civitai_lora(
    cfg: dict[str, Any],
    *,
    filename: str,
    version_id: str | int,
    force: bool = False,
) -> Path:
    """Download a LoRA into Stability Matrix Lora folder."""
    models = Path(cfg.get("stability_matrix", {}).get("models", ""))
    dest = models / "Lora" / filename
    return download_civitai_checkpoint(
        version_id=version_id,
        dest=dest,
        api_key=civitai_api_key(cfg),
        force=force,
    )

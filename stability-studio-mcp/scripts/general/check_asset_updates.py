"""Check Civitai/HF for newer versions of local checkpoints and catalog LoRAs."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio.config import catalog_path, load_config  # noqa: E402


def civitai_key(cfg: dict) -> str:
    return (
        (cfg.get("civitai") or {}).get("api_key")
        or os.environ.get("CIVITAI_API_TOKEN")
        or os.environ.get("CIVITAI_API_KEY")
        or ""
    ).strip()


def read_cm_info(path: Path) -> dict[str, Any] | None:
    sidecar = path.parent / f"{path.stem}.cm-info.json"
    if not sidecar.is_file():
        return None
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def fetch_civitai_model(model_id: int, api_key: str) -> dict[str, Any] | None:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        r = requests.get(
            f"https://civitai.com/api/v1/models/{model_id}",
            headers=headers,
            timeout=30,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}


def check_checkpoint(path: Path, api_key: str) -> dict[str, Any]:
    info = read_cm_info(path) or {}
    entry: dict[str, Any] = {
        "file": path.name,
        "path": str(path),
        "size_gb": round(path.stat().st_size / (1024**3), 2),
        "local_version_id": info.get("VersionId"),
        "local_version_name": info.get("VersionName"),
        "civitai_model_id": info.get("ModelId"),
        "model_name": info.get("ModelName"),
    }
    mid = info.get("ModelId")
    if not mid:
        entry["status"] = "no_civitai_metadata"
        return entry

    remote = fetch_civitai_model(int(mid), api_key)
    if not remote or remote.get("error"):
        entry["status"] = "civitai_lookup_failed"
        entry["error"] = (remote or {}).get("error", "unknown")
        return entry

    versions = remote.get("modelVersions") or []
    if not versions:
        entry["status"] = "no_versions_listed"
        return entry

    latest = versions[0]
    entry["latest_version_id"] = latest.get("id")
    entry["latest_version_name"] = latest.get("name")
    entry["latest_published"] = latest.get("publishedAt")
    entry["civitai_page"] = f"https://civitai.com/models/{mid}?modelVersionId={latest.get('id')}"

    local_vid = info.get("VersionId")
    if local_vid and int(local_vid) == int(latest.get("id")):
        entry["status"] = "up_to_date"
    elif local_vid:
        entry["status"] = "update_available"
        # find local version index
        for v in versions:
            if int(v.get("id")) == int(local_vid):
                entry["local_published"] = v.get("publishedAt")
                break
    else:
        entry["status"] = "unknown_local_version"
    return entry


def catalog_download_targets(cfg: dict) -> list[dict[str, Any]]:
    import yaml

    cat = yaml.safe_load(catalog_path(cfg).read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for sid, style in (cat.get("styles") or {}).items():
        dl = style.get("download") or {}
        if dl.get("civitai_model_id"):
            out.append(
                {
                    "kind": "checkpoint",
                    "style": sid,
                    "civitai_model_id": int(dl["civitai_model_id"]),
                    "civitai_version_id": dl.get("civitai_version_id"),
                }
            )
        for ld in style.get("lora_downloads") or []:
            if ld.get("civitai_version_id"):
                out.append(
                    {
                        "kind": "lora",
                        "style": sid,
                        "file": ld.get("file"),
                        "civitai_version_id": ld.get("civitai_version_id"),
                    }
                )
    return out


def main() -> None:
    cfg = load_config()
    api_key = civitai_key(cfg)
    sm_ckpt = Path(cfg["stability_matrix"]["models"]) / "StableDiffusion"

    report: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checkpoints": [],
        "catalog_entries": [],
        "summary": {},
    }

    for path in sorted(sm_ckpt.glob("*.safetensors")):
        report["checkpoints"].append(check_checkpoint(path, api_key))

    for item in catalog_download_targets(cfg):
        vid = item.get("civitai_version_id")
        if item.get("civitai_model_id"):
            remote = fetch_civitai_model(int(item["civitai_model_id"]), api_key)
            if remote and not remote.get("error"):
                latest = (remote.get("modelVersions") or [{}])[0]
                item["latest_version_id"] = latest.get("id")
                item["latest_version_name"] = latest.get("name")
                if vid and int(vid) != int(latest.get("id") or 0):
                    item["status"] = "catalog_version_behind"
                elif vid:
                    item["status"] = "catalog_up_to_date"
        report["catalog_entries"].append(item)

    statuses = [c["status"] for c in report["checkpoints"]]
    report["summary"] = {
        "total_checkpoints": len(report["checkpoints"]),
        "up_to_date": sum(1 for s in statuses if s == "up_to_date"),
        "update_available": sum(1 for s in statuses if s == "update_available"),
        "no_metadata": sum(1 for s in statuses if s == "no_civitai_metadata"),
    }

    out = ROOT / "outputs" / "asset_update_check.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

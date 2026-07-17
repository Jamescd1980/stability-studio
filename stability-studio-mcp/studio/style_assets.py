"""Image style asset checks and Hugging Face downloads (Flux2 Klein companions, etc.)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from studio.comfy_remote_models import (
    checkpoint_available,
    companion_available,
    file_has_payload,
    unet_available,
)
from studio.wan_assets import _find_file, download_asset, hf_download_url, model_dirs

CHECKPOINTS_FOLDER = "StableDiffusion"

# Downloadable companion files keyed by filename (Flux2 Klein 9B defaults).
FLUX2_COMPANION_DOWNLOADS: dict[str, dict[str, str]] = {
    "qwen_3_8b_fp8mixed.safetensors": {
        "folder": "text_encoders",
        "repo": "Comfy-Org/flux2-klein-9B",
        "path": "split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors",
        "size_hint": "~8 GB",
    },
    "qwen_3_4b.safetensors": {
        "folder": "text_encoders",
        "repo": "Comfy-Org/flux2-klein",
        "path": "split_files/text_encoders/qwen_3_4b.safetensors",
        "size_hint": "~8 GB",
    },
    "full_encoder_small_decoder.safetensors": {
        "folder": "vae",
        "repo": "black-forest-labs/FLUX.2-small-decoder",
        "path": "full_encoder_small_decoder.safetensors",
        "size_hint": "~350 MB",
    },
    "flux2-vae.safetensors": {
        "folder": "vae",
        "repo": "Comfy-Org/flux2-dev",
        "path": "split_files/vae/flux2-vae.safetensors",
        "size_hint": "~350 MB",
    },
}


def _models_root(cfg: dict[str, Any]) -> Path:
    return Path(cfg.get("stability_matrix", {}).get("models", ""))


def _checkpoint_path(cfg: dict[str, Any], filename: str) -> Path | None:
    root = _models_root(cfg)
    ckpt_dir = root / CHECKPOINTS_FOLDER
    if not ckpt_dir.is_dir():
        return None
    direct = ckpt_dir / filename
    if file_has_payload(direct):
        return direct
    for hit in ckpt_dir.rglob(filename):
        if file_has_payload(hit):
            return hit
    return None


def _unet_path(cfg: dict[str, Any], filename: str) -> tuple[Path | None, str | None]:
    """Return (path, location) where location is diffusion_models or checkpoints."""
    dirs = model_dirs(cfg)
    found = _find_file(filename, dirs, "diffusion_models")
    if found and file_has_payload(found):
        return found, "diffusion_models"
    ckpt = _checkpoint_path(cfg, filename)
    if ckpt:
        return ckpt, "checkpoints_only"
    ok, source = unet_available(cfg, filename)
    if ok and source == "comfyui":
        return Path(f"comfyui://{filename}"), "comfyui_remote"
    return None, None


def ensure_unet_in_diffusion_models(cfg: dict[str, Any], filename: str) -> dict[str, Any]:
    """Hard-link checkpoint into DiffusionModels when needed for UNETLoader."""
    dirs = model_dirs(cfg)
    dest_dir = dirs.get("diffusion_models")
    if dest_dir is None:
        raise ValueError("DiffusionModels folder not configured")
    dest = dest_dir / filename
    if dest.is_file():
        return {"filename": filename, "action": "already_present", "path": str(dest)}

    src = _checkpoint_path(cfg, filename)
    if src is None:
        raise FileNotFoundError(f"Checkpoint not found: {filename}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        dest.hardlink_to(src)
        return {"filename": filename, "action": "hardlinked", "path": str(dest), "source": str(src)}
    except OSError:
        import shutil

        shutil.copy2(src, dest)
        return {"filename": filename, "action": "copied", "path": str(dest), "source": str(src)}


def check_style_assets(
    cfg: dict[str, Any],
    catalog: Any,
    style_id: str,
) -> dict[str, Any]:
    """Return installed/missing files and setup notes for a catalog style."""
    sid = catalog._find_style_key(style_id)
    style = catalog.styles[sid]
    arch = catalog.resolve_architecture(sid)
    family = catalog.resolve_family(arch)

    installed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    setup_notes: list[str] = list(family.get("setup_notes") or [])

    ckpt = style.get("checkpoint", "")
    flux2 = style.get("flux2", {})

    if arch == "flux2_klein":
        unet_path, location = _unet_path(cfg, ckpt)
        if unet_path and location == "diffusion_models":
            installed.append({"role": "unet", "filename": ckpt, "path": str(unet_path)})
        elif unet_path and location == "comfyui_remote":
            installed.append(
                {
                    "role": "unet",
                    "filename": ckpt,
                    "path": str(unet_path),
                    "source": "comfyui",
                }
            )
        elif unet_path and location == "checkpoints_only":
            installed.append(
                {
                    "role": "unet",
                    "filename": ckpt,
                    "path": str(unet_path),
                    "warning": "In StableDiffusion only — hard-link to DiffusionModels for UNETLoader",
                }
            )
            setup_notes.append(
                f"Run download_style_assets(style='{sid}', link_unet=true) or hard-link "
                f"{ckpt} from StableDiffusion to DiffusionModels"
            )
        else:
            missing.append({"role": "unet", "filename": ckpt, "folder": "StableDiffusion or DiffusionModels"})

        for role, key in (("clip", "clip"), ("vae", "vae")):
            req = next((r for r in family.get("requires", []) if r.get("role") == role), {})
            fname = flux2.get(key) or req.get("default", "")
            if not fname:
                continue
            folder_key = req.get("folder", "text_encoders" if role == "clip" else "vae")
            dirs = model_dirs(cfg)
            found = _find_file(fname, dirs, folder_key)
            if found and file_has_payload(found):
                installed.append({"role": role, "filename": fname, "path": str(found)})
            else:
                ok_r, src = companion_available(cfg, fname, role=role)
                if ok_r:
                    installed.append(
                        {
                            "role": role,
                            "filename": fname,
                            "path": f"comfyui://{fname}",
                            "source": src,
                        }
                    )
                else:
                    item: dict[str, Any] = {"role": role, "filename": fname, "folder": folder_key}
                    dl = FLUX2_COMPANION_DOWNLOADS.get(fname)
                    if dl:
                        item.update(dl)
                        item["download_url"] = hf_download_url(dl["repo"], dl["path"])
                    missing.append(item)
    else:
        # SDXL / Pony — single checkpoint (local disk or live ComfyUI)
        if not ckpt:
            missing.append({"role": "checkpoint", "filename": "(none configured)"})
        else:
            found = _checkpoint_path(cfg, ckpt)
            if found:
                installed.append({"role": "checkpoint", "filename": ckpt, "path": str(found)})
            else:
                ok_r, src = checkpoint_available(cfg, ckpt)
                if ok_r:
                    installed.append(
                        {
                            "role": "checkpoint",
                            "filename": ckpt,
                            "path": f"comfyui://{ckpt}",
                            "source": src,
                        }
                    )
                else:
                    item: dict[str, Any] = {
                        "role": "checkpoint",
                        "filename": ckpt,
                        "folder": CHECKPOINTS_FOLDER,
                    }
                    dl_meta = style.get("download") or {}
                    if dl_meta.get("source") == "civitai":
                        item.update(
                            {
                                "source": "civitai",
                                "civitai_version_id": dl_meta.get("civitai_version_id"),
                                "civitai_page": dl_meta.get("civitai_page"),
                                "size_hint": dl_meta.get("size_hint"),
                                "download_hint": (
                                    "Set civitai.api_key in config.yaml then call download_style_assets"
                                ),
                            }
                        )
                    missing.append(item)

    ready = len(missing) == 0 and not any(i.get("warning") for i in installed)

    return {
        "style_id": sid,
        "architecture": arch,
        "family_label": family.get("label", arch),
        "workflow": family.get("workflow"),
        "typical_defaults": family.get("typical_defaults", {}),
        "prompt_style": family.get("prompt_style"),
        "installed": installed,
        "missing": missing,
        "setup_notes": setup_notes,
        "common_errors": family.get("common_errors", []),
        "ready": ready,
    }


def check_all_style_assets(cfg: dict[str, Any], catalog: Any) -> dict[str, Any]:
    by_style = {
        sid: check_style_assets(cfg, catalog, sid) for sid in catalog.styles.keys()
    }
    return {
        "styles": by_style,
        "summary": {
            sid: {"ready": data["ready"], "architecture": data["architecture"], "missing_count": len(data["missing"])}
            for sid, data in by_style.items()
        },
    }


def download_style_assets(
    cfg: dict[str, Any],
    catalog: Any,
    style_id: str,
    *,
    link_unet: bool = True,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Download missing style assets (Civitai checkpoints, Flux2 companions, UNet links)."""
    sid = catalog._find_style_key(style_id)
    style = catalog.styles[sid]
    status = check_style_assets(cfg, catalog, sid)
    results: list[dict[str, Any]] = []

    needs_ckpt = any(m.get("role") == "checkpoint" for m in status["missing"])
    dl_meta = style.get("download") or {}
    if needs_ckpt and dl_meta.get("source") == "civitai":
        try:
            from studio.civitai_download import download_style_checkpoint

            path = download_style_checkpoint(cfg, style, force=force)
            results.append({"checkpoint": str(path), "ok": True})
            status = check_style_assets(cfg, catalog, sid)
        except Exception as exc:
            results.append(
                {
                    "checkpoint": style.get("checkpoint"),
                    "ok": False,
                    "error": str(exc),
                    "civitai_page": dl_meta.get("civitai_page"),
                }
            )
            return results

    if needs_ckpt and dl_meta.get("source") == "huggingface" and dl_meta.get("repo"):
        ckpt_name = style.get("checkpoint", "")
        dest_dir = _models_root(cfg) / CHECKPOINTS_FOLDER
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / ckpt_name
        if dest.is_file() and not force:
            results.append({"checkpoint": str(dest), "ok": True, "skipped": True})
        else:
            try:
                from huggingface_hub import hf_hub_download

                fetched = Path(
                    hf_hub_download(dl_meta["repo"], dl_meta["path"], force_download=force)
                )
                if fetched.resolve() != dest.resolve():
                    if dest.is_file():
                        dest.unlink()
                    dest.write_bytes(fetched.read_bytes())
                results.append({"checkpoint": str(dest), "ok": True})
                status = check_style_assets(cfg, catalog, sid)
            except Exception as exc:
                results.append(
                    {
                        "checkpoint": ckpt_name,
                        "ok": False,
                        "error": str(exc),
                        "repo": dl_meta.get("repo"),
                    }
                )
                return results

    for entry in status["missing"]:
        fname = entry.get("filename", "")
        dl = FLUX2_COMPANION_DOWNLOADS.get(fname)
        if not dl or not dl.get("repo"):
            results.append({"filename": fname, "skipped": True, "reason": "no automatic download"})
            continue
        try:
            path = download_asset(cfg, {**dl, "filename": fname}, force=force)
            results.append({"filename": fname, "path": str(path), "ok": True})
        except Exception as exc:
            results.append({"filename": fname, "ok": False, "error": str(exc)})

    if link_unet and status["architecture"] == "flux2_klein":
        ckpt = catalog.styles[status["style_id"]].get("checkpoint", "")
        if ckpt:
            try:
                results.append({"link_unet": ensure_unet_in_diffusion_models(cfg, ckpt)})
            except Exception as exc:
                results.append({"link_unet": {"ok": False, "error": str(exc)}})

    return results

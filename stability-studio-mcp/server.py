#!/usr/bin/env python3
"""Stability Studio MCP — style-aware local image/video generation for Stability Matrix."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure package imports work when launched directly
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP

from studio.catalog import StyleCatalog
from studio.comfy_deps import (
    NODE_PACKAGES,
    check_node_types,
    check_workflow_dependencies,
    comfy_custom_nodes_dir,
    fetch_installed_node_types,
    install_node_packages,
    install_workflow_dependencies,
    packages_for_missing_nodes,
)
from studio.config import catalog_path, load_config
from studio.engine import GenerationEngine
from studio.model_scanner import scan_checkpoints, scan_loras, suggest_styles_from_models
from studio.wan_assets import check_all_video_assets, download_missing
from studio.wan_video_loras import (
    check_wan_video_loras as _check_wan_video_loras_status,
    download_wan_video_loras as _fetch_wan_video_loras,
)
from studio.style_assets import (
    check_all_style_assets,
    check_style_assets as _check_style_assets_impl,
    download_style_assets as fetch_style_assets,
)
from studio.moss_assets import MOSS_NODES, check_moss_assets as _check_moss_assets_status, download_moss_models, media_paths
from studio.wan2gp_assets import check_wan2gp_assets as _check_wan2gp_assets_status, download_wan2gp_lightning
from studio.edit_pipeline import ART_FOOD_GROUPS, plan_edit
from studio.scene_sequence import plan_scene_sequence
from studio.onboarding_context import build_onboarding_context
from studio.storyboard import (
    check_storyboard_readiness as _check_storyboard_readiness,
    plan_storyboard_scene as _plan_storyboard_scene,
)
from studio.storyboard_sheet import (
    export_renpy_skeleton as _export_renpy_skeleton,
    init_chapter_sheet as _init_chapter_sheet,
    load_sheet as _load_storyboard_sheet,
    rows_needing_generation as _rows_needing_generation,
    sheet_path as _storyboard_sheet_path,
    validate_sheet as _validate_storyboard_sheet,
)
from studio.project_context import (
    append_backlog as _append_project_log,
    build_agent_briefing as _build_agent_briefing,
    init_context as _init_project_context,
    update_context as _update_project_context,
)
from studio.prompt_log import (
    log_prompt_only as _log_prompt_only,
    log_from_generation_result as _log_from_generation_result,
    prompt_log_path as _prompt_log_path,
    read_prompt_log as _read_prompt_log,
)
from studio.version_info import build_info
from studio.error_messages import humanize_error
from studio.gpu_backend import (
    gpu_backend_policy_for_context,
    inspect_gpu_backend,
    release_gpu_lock as _release_gpu_lock,
)
from studio.wan2gp_runner import check_wan2gp_runtime as _check_wan2gp_runtime
from studio.wan2gp_settings import plan_wan2gp_job as _plan_wan2gp_job
from studio.face_detail_assets import (
    check_face_detail_dependencies as _check_face_detail_dependencies,
    download_face_detail_assets as _download_face_detail_assets,
    install_face_detail_dependencies as _install_face_detail_dependencies,
    setup_face_detail as _setup_face_detail,
)
from studio.image_editing_assets import (
    check_image_editing_readiness as _check_image_editing_readiness,
    check_sd15_controlnet_assets,
    download_sd15_controlnet_assets as _download_sd15_controlnet_impl,
    setup_image_editing as _setup_image_editing,
)
from studio.ip_adapter_assets import (
    check_controlnet_assets as _check_controlnet_assets,
    check_controlnet_dependencies as _check_controlnet_dependencies,
    check_ip_adapter_assets as _check_ip_adapter_assets,
    check_ip_adapter_dependencies as _check_ip_adapter_dependencies,
    download_controlnet_assets as _download_controlnet_assets,
    download_ip_adapter_assets as _download_ip_adapter_assets,
    install_controlnet_dependencies as _install_controlnet_dependencies,
    install_ip_adapter_dependencies as _install_ip_adapter_dependencies,
)
from studio.pose_control import (
    OPENPOSE_EDITORS,
    PREPROCESSORS,
    check_pose_control_readiness as _check_pose_control_readiness,
    setup_pose_control as _setup_pose_control,
)

mcp = FastMCP(
    "stability-studio",
    instructions=(
        "Local image and video generation for Stability Matrix. "
        "Call get_generation_context first — it includes hardware_profile and generation_limits "
        "(GPU VRAM caps). Stay within generation_limits unless the user explicitly asks for more. "
        "New users: call get_onboarding_context first — guided tiers, VRAM routing, install checklist (onboarding/). "
        "Not a one-click installer; AI-assisted ComfyUI workflow. "
        "≥24 GB VRAM: ComfyUI only, do not offer Wan2GP. ≤16 GB: Wan2GP only if user explicitly wants hero/lip sync. "
        "Prefer prompt quality (face, hands, anatomy) over max resolution. "
        "Use style ids from the catalog (anime, ilustmix, divine_elegance, cyberpunk, photorealistic_pony, …). "
        "Four art food groups: anime, fantasy, cyberpunk, photoreal — pass food_group= to edit_image. "
        "Each style has an architecture (sd15, sdxl, pony_sdxl, flux2_klein) — see get_generation_context. "
        "Image edits: setup_image_editing() then edit_image(image_path, instruction, food_group=...). "
        "Before first image on a new PC: check style_readiness in get_generation_context; "
        "Flux2: check_style_assets / download_style_assets(style='miracle_nsfw'). "
        "Aliases work: 'illustrious'→anime, 'ragnarok'→juggernaut, 'realistic'→photorealistic. "
        "Pass checkpoint= to override. For video: call check_comfyui_dependencies(workflow_id) first; "
        "if missing nodes, call install_comfyui_dependencies then restart ComfyUI from Stability Matrix. "
        "Use generate_video(mode=t2v|i2v|v2v, workflow_id=t2v|i2v_5b|i2v_5b_painter|v2v_5b|v2v_5b_painter|i2v|i2v_gpu) — short ids only. "
        "Default I2V: i2v_5b (Wan 2.2 TI2V-5B). workflow_id=i2v_5b_painter or use_painter_i2v=true for PainterI2V motion. Optional LoRAs: lora_ids / lora_bundle. "
        "Optional Wan video LoRAs: check_wan_video_loras / download_wan_video_loras(bundle=smooth_character|walk_cycle|cinematic_church). "
        "Pass lora_ids or lora_bundle to generate_video. Call check_wan_assets / download_wan_assets for base models. "
        "Audio (MOSS-TTS): check_moss_assets → download_moss_assets → generate_audio(mode=speech|sound_effect|voice_design). "
        "GPU policy (16 GB): call check_gpu_backend before generate_video / generate_audio / generate_video_hero. "
        "Draft I2V: generate_video(mode=i2v, workflow_id=i2v_5b). Hero I2V: stop ComfyUI → check_gpu_backend → "
        "generate_video_hero (auto-starts Wan2GP MCP on :7867). Never run ComfyUI and Wan2GP UI together. "
        "Offline agents (Jan, LM Studio): check_gpu_backend is mandatory — conflicts return gpu_backend_conflict. "
        "Media output paths: get_generation_context.media_paths. "
        "For inpaint_advanced (flags, reference objects): setup_ip_adapter or "
        "install_ip_adapter_dependencies + download_ip_adapter_assets — then restart ComfyUI."
    ),
)

_cfg = load_config()
_catalog = StyleCatalog(catalog_path(_cfg), _cfg)
_engine = GenerationEngine(_cfg, _catalog)


def _comfy_url() -> str:
    return _cfg.get("comfyui", {}).get("url", "http://127.0.0.1:8188")


def _parse_lora_ids_arg(value: Any = None) -> list[str] | None:
    """Accept comma-separated string or JSON/list — small VLMs often pass arrays."""
    if value is None or value == "":
        return None
    if isinstance(value, list):
        ids = [str(item).strip() for item in value if str(item).strip()]
        return ids or None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return _parse_lora_ids_arg(parsed)
        return [part.strip() for part in text.split(",") if part.strip()] or None
    return [str(value).strip()] if str(value).strip() else None


def _delivery_project_root(project_dir: str = "") -> Path | None:
    from studio.storyboard_cli import resolve_project_dir

    if project_dir:
        return resolve_project_dir(project_dir)
    raw = (_cfg.get("outputs") or {}).get("delivery")
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _load_ui_workflow(workflow_id: str = "", mode: str = "t2v") -> dict:
    ui, _ = _engine.load_ui_workflow(workflow_id or None, mode)
    return ui


@mcp.tool()
def get_generation_context() -> str:
    """Return installed models, styles, LoRAs, video workflows, GPU profile, and generation limits."""
    ctx = _catalog.get_generation_context()
    ctx["backend_status"] = _engine.backend_status()
    ctx.update(_engine.hardware_context())
    ctx["wan_video_assets"] = check_all_video_assets(_cfg)
    ctx["wan_video_loras"] = _check_wan_video_loras_status(_cfg)
    ctx["style_readiness"] = check_all_style_assets(_cfg, _catalog)
    ctx["ip_adapter_readiness"] = _check_ip_adapter_assets(_cfg, include_optional=False)
    comfy_url = _comfy_url()
    ctx["ip_adapter_dependencies"] = _check_ip_adapter_dependencies(
        _cfg, comfy_url, include_depth=False
    )
    ctx["image_editing_readiness"] = _check_image_editing_readiness(_cfg, comfy_url)
    ctx["face_detail_readiness"] = _check_face_detail_dependencies(_cfg, comfy_url)
    ctx["art_food_groups"] = _catalog.art_food_groups or ART_FOOD_GROUPS
    ctx["moss_audio"] = _check_moss_assets_status(_cfg)
    ctx["wan2gp_assets"] = _check_wan2gp_assets_status(_cfg)
    ctx["gpu_backend_policy"] = gpu_backend_policy_for_context(_cfg)
    ctx["media_paths"] = media_paths(_cfg)
    ver = build_info()
    ver["mcp_tool_count"] = MCP_TOOL_COUNT
    ctx["studio_version"] = ver
    ctx["pose_control_readiness"] = _check_pose_control_readiness(_cfg, comfy_url)
    ctx["restart_guide"] = "RESTART-GUIDE.md — ComfyUI vs MCP vs parallel GPU jobs"
    return json.dumps(ctx, indent=2)


@mcp.tool()
def get_onboarding_context() -> str:
    """
    Guided setup for less technical users — tiers, questions, VRAM routing, install checklist.

    Call at the start of a setup session before installing models or offering Wan2GP.
    Read onboarding/ONBOARDING.md for the full conversational playbook.
    """
    hw = _engine.hardware_context()
    return json.dumps(build_onboarding_context(_cfg, hardware=hw), indent=2)


@mcp.tool()
def check_style_assets(style: str = "") -> str:
    """
    Check installed vs missing model files for image styles (SDXL, Pony, Flux2 Klein).

    Args:
        style: Catalog style id (e.g. miracle_nsfw, photorealistic_pony). Empty = all styles.
    """
    if style:
        return json.dumps(_check_style_assets_impl(_cfg, _catalog, style), indent=2)
    return json.dumps(check_all_style_assets(_cfg, _catalog), indent=2)


@mcp.tool()
def download_style_assets(
    style: str = "miracle_nsfw",
    link_unet: bool = True,
    force: bool = False,
) -> str:
    """
    Download missing Flux2 Klein companion files (text encoder, VAE) and link UNet to DiffusionModels.

    Args:
        style: Catalog style id (default miracle_nsfw / Flux2).
        link_unet: Hard-link checkpoint from StableDiffusion into DiffusionModels for UNETLoader.
        force: Re-download even when files exist.
    """
    results = fetch_style_assets(_cfg, _catalog, style, link_unet=link_unet, force=force)
    summary = _check_style_assets_impl(_cfg, _catalog, style)
    return json.dumps({"downloads": results, "status": summary}, indent=2)


@mcp.tool()
def check_wan_assets(workflow_id: str = "") -> str:
    """
    Check installed vs missing LoRAs/models for Wan video workflows (I2V, T2V).

    Args:
        workflow_id: Catalog id (i2v_5b, i2v, i2v_gpu, i2v_wan21, t2v). Empty = all workflows + V2V note.
    """
    if workflow_id:
        from studio.wan_assets import check_workflow_assets

        return json.dumps(check_workflow_assets(_cfg, workflow_id), indent=2)
    return json.dumps(check_all_video_assets(_cfg), indent=2)


@mcp.tool()
def download_wan_assets(
    workflow_id: str = "i2v",
    include_large: bool = False,
    force: bool = False,
) -> str:
    """
    Download missing Wan LoRAs/models from Hugging Face into Stability Matrix folders.

    Args:
        workflow_id: i2v_5b (default I2V), t2v, i2v, i2v_wan21, etc.
        include_large: If true, also download multi-GB diffusion / text encoder files.
        force: Re-download even when files exist.
    """
    results = download_missing(
        _cfg,
        workflow_id,
        include_large=include_large,
        force=force,
    )
    summary = check_all_video_assets(_cfg)
    return json.dumps({"downloads": results, "summary": summary["summary"]}, indent=2)


@mcp.tool()
def check_wan_video_loras(lora_ids: str | list[str] = "") -> str:
    """
    Check optional Wan 2.2 video LoRAs (motion, face, lighting, camera).

    Args:
        lora_ids: Catalog id(s): comma-separated string or list (e.g. face_naturalizer). Empty = all.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    return json.dumps(_check_wan_video_loras_status(_cfg, ids), indent=2)


@mcp.tool()
def download_wan_video_loras(
    lora_ids: str | list[str] = "",
    bundle: str = "",
    force: bool = False,
) -> str:
    """
    Download optional Wan video LoRAs from Hugging Face into Stability Matrix Lora/.

    Args:
        lora_ids: Catalog id(s): comma-separated string or list. Empty = all (or bundle only if set).
        bundle: smooth_character | walk_cycle | cinematic_church | motion_boost (merges with lora_ids).
        force: Re-download even when present.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    results = _fetch_wan_video_loras(_cfg, lora_ids=ids, bundle=bundle, force=force)
    summary = _check_wan_video_loras_status(_cfg, ids)
    return json.dumps({"downloads": results, "status": summary}, indent=2)


@mcp.tool()
def check_painter_i2v_dependencies() -> str:
    """Check whether ComfyUI has the PainterI2V custom node (Wan 2.2 motion_amplitude)."""
    comfy_url = _comfy_url()
    try:
        installed = fetch_installed_node_types(comfy_url)
        ready = "PainterI2V" in installed
        return json.dumps(
            {
                "ready": ready,
                "node_type": "PainterI2V",
                "package": NODE_PACKAGES["PainterI2V"],
                "custom_nodes_dir": str(comfy_custom_nodes_dir(_cfg)),
            },
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"ready": False, "error": str(exc)}, indent=2)


@mcp.tool()
def install_painter_i2v_dependencies() -> str:
    """Install ComfyUI-PainterI2V into ComfyUI custom_nodes. Restart ComfyUI after."""
    comfy_url = _comfy_url()
    report = check_node_types(cfg=_cfg, comfy_url=comfy_url, required={"PainterI2V"})
    pkgs = report.get("installable_packages") or packages_for_missing_nodes({"PainterI2V"})
    installs = install_node_packages(_cfg, pkgs) if pkgs else []
    return json.dumps(
        {
            **report,
            "install_results": installs,
            "custom_nodes_dir": str(comfy_custom_nodes_dir(_cfg)),
            "next_steps": [
                "Restart ComfyUI from Stability Matrix (required for PainterI2V to load).",
            ],
        },
        indent=2,
    )


@mcp.tool()
def check_ip_adapter_assets(include_optional: bool = False) -> str:
    """
    Check IP-Adapter / CLIP-Vision models for inpaint_advanced (SDXL reference edits).

    Args:
        include_optional: Also check optional ControlNet depth model (~2.5 GB).
    """
    return json.dumps(_check_ip_adapter_assets(_cfg, include_optional=include_optional), indent=2)


@mcp.tool()
def download_ip_adapter_assets(
    include_optional: bool = False,
    force: bool = False,
) -> str:
    """
    Download IP-Adapter SDXL models into ComfyUI models folders and fetch bundled flag reference.

    Args:
        include_optional: Also download ControlNet depth SDXL (~2.5 GB).
        force: Re-download even when files exist.
    """
    results = _download_ip_adapter_assets(
        _cfg,
        include_optional=include_optional,
        force=force,
    )
    summary = _check_ip_adapter_assets(_cfg, include_optional=include_optional)
    return json.dumps({"downloads": results, "status": summary}, indent=2)


@mcp.tool()
def check_ip_adapter_dependencies(include_depth: bool = False) -> str:
    """Check ComfyUI custom nodes required for inpaint_advanced (IP-Adapter Plus, optional depth aux)."""
    comfy_url = _comfy_url()
    return json.dumps(
        _check_ip_adapter_dependencies(_cfg, comfy_url, include_depth=include_depth),
        indent=2,
    )


@mcp.tool()
def install_ip_adapter_dependencies(include_depth: bool = True) -> str:
    """
    Git-clone ComfyUI_IPAdapter_plus (and optional ControlNet aux) into ComfyUI custom_nodes.

    Restart ComfyUI from Stability Matrix after install, then re-run check_ip_adapter_dependencies.
    """
    comfy_url = _comfy_url()
    report = _install_ip_adapter_dependencies(_cfg, comfy_url, include_depth=include_depth)
    return json.dumps(report, indent=2)


@mcp.tool()
def setup_ip_adapter(
    include_depth: bool = False,
    include_optional_models: bool = False,
    force: bool = False,
) -> str:
    """
    One-shot setup for inpaint_advanced: install custom nodes, download models, fetch Irish flag reference.

    After this completes, restart ComfyUI from Stability Matrix if any nodes were installed.
  """
    comfy_url = _comfy_url()
    deps = _install_ip_adapter_dependencies(_cfg, comfy_url, include_depth=include_depth)
    downloads = _download_ip_adapter_assets(
        _cfg,
        include_optional=include_optional_models or include_depth,
        force=force,
    )
    assets = _check_ip_adapter_assets(
        _cfg, include_optional=include_optional_models or include_depth
    )
    deps_after = _check_ip_adapter_dependencies(_cfg, comfy_url, include_depth=include_depth)
    return json.dumps(
        {
            "install": deps,
            "downloads": downloads,
            "assets": assets,
            "dependencies_after": deps_after,
            "next_steps": [
                "Restart ComfyUI from Stability Matrix if install_results is non-empty.",
                "Call edit_image or inpaint_advanced with flag_reference='ireland' and mask_region='right_building'.",
            ],
        },
        indent=2,
    )


@mcp.tool()
def list_styles() -> str:
    """List human-friendly style presets (photorealistic, anime, etc.)."""
    return json.dumps(_catalog.list_styles(), indent=2)


@mcp.tool()
def list_checkpoints() -> str:
    """List checkpoint files scanned from Stability Matrix."""
    models_dir = Path(_cfg["stability_matrix"]["models"])
    return json.dumps(scan_checkpoints(models_dir), indent=2)


@mcp.tool()
def list_loras() -> str:
    """List LoRA files from Stability Matrix and extra folders."""
    models_dir = Path(_cfg["stability_matrix"]["models"])
    return json.dumps(scan_loras(models_dir, _cfg.get("extra_lora_paths")), indent=2)


@mcp.tool()
def list_video_workflows() -> str:
    """List video workflows. Use the short id field (t2v, i2v_5b, i2v, i2v_wan21) as workflow_id."""
    data = {
        "workflows": _catalog.list_video_workflow_entries(),
        "on_disk": _catalog.get_generation_context()["video_workflow_files"],
        "usage": "Pass workflow_id='i2v_5b' (default I2V), 't2v', or 'i2v' — not the .json filename.",
    }
    return json.dumps(data, indent=2)


@mcp.tool()
def check_backends() -> str:
    """Check whether ComfyUI and InvokeAI are reachable."""
    return json.dumps(_engine.backend_status(), indent=2)


@mcp.tool()
def scan_models() -> str:
    """Scan local models and return suggested style → checkpoint mappings."""
    hints = _catalog.refresh_scan_hints()
    return json.dumps(
        {
            "suggested_mappings": hints,
            "note": "Update catalog.yaml styles.checkpoint with these filenames to match your library.",
        },
        indent=2,
    )


@mcp.tool()
def check_comfyui_dependencies(workflow_id: str = "", mode: str = "t2v") -> str:
    """
    Check whether ComfyUI has all custom nodes required by a video workflow.

    Args:
        workflow_id: Catalog id (t2v, i2v, i2v_wan21, t2v_wan22). Empty = auto by mode.
        mode: t2v or i2v when workflow_id is empty.
    """
    ui_workflow = _load_ui_workflow(workflow_id, mode)
    comfy_url = _comfy_url()
    report = check_workflow_dependencies(cfg=_cfg, ui_workflow=ui_workflow, comfy_url=comfy_url)
    report["workflow_id"] = workflow_id or f"auto:{mode}"
    return json.dumps(report, indent=2)


@mcp.tool()
def install_comfyui_dependencies(
    workflow_id: str = "",
    mode: str = "t2v",
    include_manager: bool = False,
) -> str:
    """
    Git-clone missing ComfyUI custom node packs for a video workflow.

    After install you MUST restart ComfyUI from Stability Matrix, then re-run
    check_comfyui_dependencies before generate_video.

    Args:
        workflow_id: Catalog id (t2v, i2v, etc.).
        mode: t2v or i2v when workflow_id is empty.
        include_manager: Also install ComfyUI-Manager (optional UI for future installs).
    """
    ui_workflow = _load_ui_workflow(workflow_id, mode)
    comfy_url = _comfy_url()
    report = install_workflow_dependencies(
        cfg=_cfg,
        ui_workflow=ui_workflow,
        comfy_url=comfy_url,
        include_manager=include_manager,
    )
    report["workflow_id"] = workflow_id or f"auto:{mode}"
    return json.dumps(report, indent=2)


@mcp.tool()
def check_face_detail_dependencies() -> str:
    """Impact Pack FaceDetailer nodes, Impact Subpack detector, and YOLO/SAM model files."""
    comfy_url = _comfy_url()
    return json.dumps(_check_face_detail_dependencies(_cfg, comfy_url), indent=2)


@mcp.tool()
def install_face_detail_dependencies() -> str:
    """
    Install ComfyUI-Impact-Pack + Impact-Subpack for FaceDetailer (ADetailer-style face pass).

    Restart ComfyUI from Stability Matrix after install, then download_face_detail_assets.
    """
    comfy_url = _comfy_url()
    return json.dumps(_install_face_detail_dependencies(_cfg, comfy_url), indent=2)


@mcp.tool()
def download_face_detail_assets(force: bool = False) -> str:
    """Download face_yolov8m.pt and sam_vit_b_01ec64.pth for FaceDetailer."""
    return json.dumps(_download_face_detail_assets(_cfg, force=force), indent=2)


@mcp.tool()
def setup_face_detail(force_download: bool = False) -> str:
    """
    One-shot FaceDetailer setup: install Impact Pack + Subpack, download detector/SAM models.

    Restart ComfyUI when restart_comfyui_required is true, then use face_detail=true on generate_image.
    """
    comfy_url = _comfy_url()
    return json.dumps(_setup_face_detail(_cfg, comfy_url, force=force_download), indent=2)


@mcp.tool()
def generate_image(
    prompt: str,
    style: str = "",
    negative_prompt: str = "",
    checkpoint: str = "",
    loras: list[dict[str, Any]] | None = None,
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    cfg: float = 0,
    seed: int = -1,
    sampler: str = "",
    scheduler: str = "",
    face_detail: bool | None = None,
    backend: str = "auto",
    content_rating: str = "open",
) -> str:
    """
    Generate an image using a style preset from list_styles().

    Args:
        prompt: What to generate.
        style: Catalog style id (ilustmix, pony, juggernaut, miracle_nsfw, …). Not checkpoint filenames — use pony not prefectPonyXL_v6. Empty = default.
        negative_prompt: Override default negative prompt.
        checkpoint: Override checkpoint filename.
        loras: Optional list of LoRAs, e.g. [{"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "weight": 0.85}].
        width, height, steps, cfg, seed: Optional overrides. Use plain integers only (e.g. width=832, height=1216). Never embed "8k" in width/height. 0 = use style default.
        sampler, scheduler: Optional overrides (empty = style/family defaults, e.g. ilustmix: euler_ancestral + normal).
        face_detail: Optional FaceDetailer second pass (ADetailer-style). None = style default (ilustmix: true).
        backend: auto, comfyui, or invoke.
        content_rating: open (default), sfw, or nsfw. Only sfw adds safety negatives.
    """
    result = _engine.generate_image(
        prompt=prompt,
        style=style or None,
        negative_prompt=negative_prompt or None,
        checkpoint=checkpoint or None,
        loras=loras or None,
        width=width or None,
        height=height or None,
        steps=steps or None,
        cfg=cfg or None,
        seed=None if seed < 0 else seed,
        sampler=sampler or None,
        scheduler=scheduler or None,
        face_detail=face_detail,
        backend=None if backend == "auto" else backend,
        content_rating=content_rating or "open",
    )
    root = _delivery_project_root()
    if root:
        logged = _log_from_generation_result(root, agent="mcp", kind="image", result=result)
        if logged:
            result["prompt_log"] = logged
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_image_guided(
    guide_image_path: str,
    prompt: str,
    style: str = "",
    negative_prompt: str = "",
    checkpoint: str = "",
    loras: list[dict[str, Any]] | None = None,
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    cfg: float = 0,
    seed: int = -1,
    ipadapter_weight: float = 0.72,
    ipadapter_weight_type: str = "style and composition",
    ipadapter_ref_size: int = 512,
    backend: str = "auto",
    content_rating: str = "open",
) -> str:
    """
    Generate from scratch with IP-Adapter locking composition to a guide image.

    Use a strong prompt for changes (e.g. add flag); raise ipadapter_weight (0.8+)
  to stay closer to the guide.
    """
    result = _engine.generate_image_guided(
        guide_image_path=guide_image_path,
        prompt=prompt,
        style=style or None,
        negative_prompt=negative_prompt or None,
        checkpoint=checkpoint or None,
        loras=loras or None,
        width=width or None,
        height=height or None,
        steps=steps or None,
        cfg=cfg or None,
        seed=None if seed < 0 else seed,
        ipadapter_weight=ipadapter_weight,
        ipadapter_weight_type=ipadapter_weight_type,
        ipadapter_ref_size=ipadapter_ref_size,
        backend=None if backend == "auto" else backend,
        content_rating=content_rating or "open",
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_image_controlnet(
    guide_image_path: str,
    prompt: str,
    style: str = "",
    negative_prompt: str = "",
    checkpoint: str = "",
    loras: list[dict[str, Any]] | None = None,
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    cfg: float = 0,
    seed: int = -1,
    depth_strength: float = 0.52,
    canny_strength: float = 0.62,
    canny_low_threshold: float = 0.25,
    canny_high_threshold: float = 0.6,
    backend: str = "auto",
    content_rating: str = "open",
) -> str:
    """
    Txt2img guided by depth + canny ControlNet maps from a reference image.

    Requires controlnet-depth-sdxl-1.0 and controlnet-canny-sdxl-1.0 plus
    comfyui_controlnet_aux (DepthAnythingPreprocessor). Call setup_controlnet first.
    """
    result = _engine.generate_image_controlnet(
        guide_image_path=guide_image_path,
        prompt=prompt,
        style=style or None,
        negative_prompt=negative_prompt or None,
        checkpoint=checkpoint or None,
        loras=loras or None,
        width=width or None,
        height=height or None,
        steps=steps or None,
        cfg=cfg or None,
        seed=None if seed < 0 else seed,
        depth_strength=depth_strength,
        canny_strength=canny_strength,
        canny_low_threshold=canny_low_threshold,
        canny_high_threshold=canny_high_threshold,
        backend=None if backend == "auto" else backend,
        content_rating=content_rating or "open",
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def check_controlnet_assets() -> str:
    """Check SDXL depth + canny ControlNet model files on disk."""
    return json.dumps(_check_controlnet_assets(_cfg), indent=2)


@mcp.tool()
def download_controlnet_assets(force: bool = False) -> str:
    """Download SDXL depth + canny ControlNet weights (~5 GB total)."""
    results = _download_controlnet_assets(_cfg, force=force)
    summary = _check_controlnet_assets(_cfg)
    return json.dumps({"downloads": results, "summary": summary}, indent=2)


@mcp.tool()
def check_controlnet_dependencies() -> str:
    """Verify ComfyUI has Canny, DepthAnythingPreprocessor, and ControlNet nodes."""
    return json.dumps(_check_controlnet_dependencies(_cfg, _comfy_url()), indent=2)


@mcp.tool()
def install_controlnet_dependencies() -> str:
    """Install comfyui_controlnet_aux for depth preprocessing. Restart ComfyUI after."""
    comfy_url = _comfy_url()
    return json.dumps(_install_controlnet_dependencies(_cfg, comfy_url), indent=2)


@mcp.tool()
def setup_image_editing(
    include_sd15_controlnet: bool = True,
    include_segmentation: bool = True,
    force_download: bool = False,
) -> str:
    """
    One-shot image-editing setup: IP-Adapter, SDXL + SD1.5 ControlNet, segmentation nodes, flag refs.

    Restart ComfyUI from Stability Matrix when restart_comfyui_required is true.
    """
    comfy_url = _comfy_url()
    return json.dumps(
        _setup_image_editing(
            _cfg,
            comfy_url,
            include_sd15_controlnet=include_sd15_controlnet,
            include_segmentation=include_segmentation,
            force=force_download,
        ),
        indent=2,
    )


@mcp.tool()
def check_image_editing_readiness() -> str:
    """IP-Adapter, ControlNet (SDXL + SD1.5), segmentation nodes, and reference assets."""
    comfy_url = _comfy_url()
    return json.dumps(_check_image_editing_readiness(_cfg, comfy_url), indent=2)


@mcp.tool()
def list_art_food_groups() -> str:
    """Four art food groups (anime, fantasy, cyberpunk, photoreal) with default styles."""
    return json.dumps(
        {
            "food_groups": _catalog.art_food_groups or ART_FOOD_GROUPS,
            "usage": "Pass food_group='anime' (or fantasy|cyberpunk|photoreal) to edit_image or generate_image.",
            "defaults": {
                k: v.get("default_style") for k, v in (_catalog.art_food_groups or ART_FOOD_GROUPS).items()
            },
        },
        indent=2,
    )


@mcp.tool()
def plan_image_edit(
    instruction: str,
    food_group: str = "",
    mode: str = "auto",
    segment_prompt: str = "",
    preserve_subject: bool = True,
) -> str:
    """Preview which pipeline edit_image would use (no GPU run)."""
    return json.dumps(
        plan_edit(
            instruction=instruction,
            food_group=food_group or None,
            mode=mode,
            segment_prompt=segment_prompt,
            preserve_subject=preserve_subject,
        ),
        indent=2,
    )


@mcp.tool()
def edit_image(
    image_path: str,
    instruction: str,
    food_group: str = "",
    style: str = "",
    mode: str = "auto",
    segment_prompt: str = "",
    mask_region: str = "",
    negative_prompt: str = "",
    reference_image_path: str = "",
    flag_reference: str = "",
    seed: int = -1,
    steps: int = 0,
    cfg: float = 0,
    denoising_strength: float = 1.0,
    ipadapter_weight: float = 0.85,
    depth_strength: float = 0.52,
    canny_strength: float = 0.62,
    preserve_subject: bool = True,
    backend: str = "auto",
    content_rating: str = "open",
) -> str:
    """
    Unified image edit from natural language. Prefer over raw inpaint/i2i for agents.

    food_group: anime (ilustmix) | fantasy (divine_elegance) | cyberpunk | photoreal.
    mode: auto | i2i | inpaint | controlnet | hybrid | hybrid_preserve.
    Call setup_image_editing() once per machine, then restart ComfyUI if needed.
    """
    result = _engine.edit_image(
        image_path=image_path,
        instruction=instruction,
        food_group=food_group or None,
        style=style or None,
        mode=mode,
        segment_prompt=segment_prompt,
        mask_region=mask_region,
        negative_prompt=negative_prompt or None,
        reference_image_path=reference_image_path or None,
        flag_reference=flag_reference,
        seed=None if seed < 0 else seed,
        steps=steps or None,
        cfg=cfg or None,
        denoising_strength=denoising_strength,
        ipadapter_weight=ipadapter_weight,
        depth_strength=depth_strength,
        canny_strength=canny_strength,
        preserve_subject=preserve_subject,
        backend=None if backend == "auto" else backend,
        content_rating=content_rating or "open",
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def download_sd15_controlnet_assets(force: bool = False) -> str:
    """Download SD 1.5 depth + canny ControlNet (~2.8 GB) for photorealistic / sd15 edits."""
    results = _download_sd15_controlnet_impl(_cfg, force=force)
    summary = check_sd15_controlnet_assets(_cfg)
    return json.dumps({"downloads": results, "summary": summary}, indent=2)


@mcp.tool()
def sync_checkpoint_architectures(apply: bool = False) -> str:
    """
    Compare catalog architecture fields to Civitai cm-info / safetensors sniff on disk.

    Set apply=true to write detected architectures into catalog.yaml (use with care).
    """
    changes = sync_catalog_architecture_from_disk(_catalog._data, _cfg, dry_run=not apply)
    if apply:
        _catalog.save()
    return json.dumps(
        {"changes": changes, "applied": apply, "count": len(changes)},
        indent=2,
    )


@mcp.tool()
def setup_controlnet(
    download_models: bool = True,
    install_nodes: bool = True,
) -> str:
    """One-shot: install ControlNet aux nodes and download depth + canny SDXL models."""
    comfy_url = _comfy_url()
    out: dict[str, Any] = {}
    if install_nodes:
        out["dependencies"] = _install_controlnet_dependencies(_cfg, comfy_url)
    if download_models:
        out["downloads"] = _download_controlnet_assets(_cfg)
    out["assets"] = _check_controlnet_assets(_cfg)
    out["dependencies_after"] = _check_controlnet_dependencies(_cfg, comfy_url)
    out["next_steps"] = [
        "Restart ComfyUI from Stability Matrix if nodes were just installed.",
        "Then call generate_image_controlnet with guide_image_path.",
    ]
    return json.dumps(out, indent=2)


@mcp.tool()
def check_pose_control_readiness() -> str:
    """OpenPose/DWPose/Canny/lineart preprocessors + OpenPose XL2 ControlNet status."""
    return json.dumps(_check_pose_control_readiness(_cfg, _comfy_url()), indent=2)


@mcp.tool()
def setup_pose_control(
    download_openpose: bool = True,
    force_download: bool = False,
) -> str:
    """
    Install pose/line preprocessors (comfyui_controlnet_aux) and download OpenPose XL2 (~2.5 GB).

    Restart ComfyUI when restart_comfyui_required is true.
  """
    return json.dumps(
        _setup_pose_control(
            _cfg,
            _comfy_url(),
            download_openpose=download_openpose,
            force_download=force_download,
        ),
        indent=2,
    )


@mcp.tool()
def list_pose_control_options() -> str:
    """Preprocessor ids, OpenPose editor URLs, and Rin kunai workflow hint."""
    return json.dumps(
        {
            "preprocessors": {k: v["label"] for k, v in PREPROCESSORS.items()},
            "openpose_editors": OPENPOSE_EDITORS,
            "pose_guided_i2i": (
                "generate_image_pose_guided(image_path=hero, pose_image_path=editor_export.png, "
                "prompt='... holding_kunai ...', style='pony', preprocess_pose=false)"
            ),
            "extract_maps": "extract_control_maps(image_path=..., maps=['openpose','canny','anime_lineart'])",
        },
        indent=2,
    )


@mcp.tool()
def extract_control_maps(
    image_path: str,
    maps: list[str] | None = None,
    resolution: int = 0,
) -> str:
    """
    Preview control maps from a photo: openpose | dwpose | canny | anime_lineart | lineart | hed.

    Canny / anime_lineart produce hardline maps like ControlNet edge guides.
    """
    result = _engine.extract_control_maps(
        image_path=image_path,
        maps=maps,
        resolution=resolution or None,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_image_pose_guided(
    image_path: str,
    pose_image_path: str,
    prompt: str,
    style: str = "pony",
    negative_prompt: str = "",
    loras: list[dict[str, Any]] | None = None,
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    cfg: float = 0,
    seed: int = -1,
    denoising_strength: float = 0.38,
    openpose_strength: float = 0.82,
    preprocess_pose: bool = False,
    sampler: str = "",
    scheduler: str = "",
) -> str:
    """
    Identity i2i + OpenPose ControlNet.

    pose_image_path: skeleton PNG from openpose-editor.vercel.app (set preprocess_pose=false),
    or a photo (set preprocess_pose=true to extract skeleton first).
    """
    result = _engine.generate_image_pose_guided(
        image_path=image_path,
        pose_image_path=pose_image_path,
        prompt=prompt,
        style=style or None,
        negative_prompt=negative_prompt or None,
        loras=loras,
        width=width or None,
        height=height or None,
        steps=steps or None,
        cfg=cfg or None,
        seed=None if seed < 0 else seed,
        denoising_strength=denoising_strength,
        openpose_strength=openpose_strength,
        preprocess_pose=preprocess_pose,
        sampler=sampler or None,
        scheduler=scheduler or None,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_image_i2i(
    image_path: str,
    prompt: str,
    style: str = "",
    negative_prompt: str = "",
    checkpoint: str = "",
    loras: list[dict[str, Any]] | None = None,
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    cfg: float = 0,
    seed: int = -1,
    denoising_strength: float = 0.45,
    sampler: str = "",
    scheduler: str = "",
    face_detail: bool | None = None,
    backend: str = "auto",
    content_rating: str = "open",
) -> str:
    """
    Image-to-image refinement. Use an existing image as the starting latent (denoising < 1.0).

    Args:
        image_path: Path to the source image (will be uploaded to ComfyUI).
        prompt: What to generate / refine toward.
        style: Style id.
        negative_prompt: Override default negative.
        checkpoint: Override checkpoint.
        loras: List of LoRAs with weights, e.g. [{"file": "...", "weight": 0.85}].
        width, height, steps, cfg, seed: Optional overrides.
        sampler, scheduler: Optional overrides (empty = style defaults).
        face_detail: Optional FaceDetailer second pass. None = style default (ilustmix: true).
        denoising_strength: 0.25–0.65 typical for face cleanup (lower = more faithful to source).
        backend: auto, comfyui, or invoke.
        content_rating: open (default), sfw, or nsfw.
    """
    result = _engine.generate_image_i2i(
        image_path=image_path,
        prompt=prompt,
        style=style or None,
        negative_prompt=negative_prompt or None,
        checkpoint=checkpoint or None,
        loras=loras or None,
        width=width or None,
        height=height or None,
        steps=steps or None,
        cfg=cfg or None,
        seed=None if seed < 0 else seed,
        denoising_strength=denoising_strength,
        sampler=sampler or None,
        scheduler=scheduler or None,
        face_detail=face_detail,
        backend=None if backend == "auto" else backend,
        content_rating=content_rating or "open",
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def inpaint_image(
    image_path: str,
    prompt: str,
    style: str = "",
    negative_prompt: str = "",
    checkpoint: str = "",
    loras: list[dict[str, Any]] | None = None,
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    cfg: float = 0,
    seed: int = -1,
    denoising_strength: float = 0.35,
    backend: str = "auto",
    content_rating: str = "open",
) -> str:
    """
    Inpainting-style edit. Best for adding/changing specific parts of an image (e.g. background elements)
    while trying to preserve the main subject.

    Args:
        image_path: Path to the source image.
        prompt: Description of the desired change (e.g. "add a large Irish flag on top of the church").
        style: Style id.
        negative_prompt: Override default negative.
        checkpoint: Override checkpoint.
        loras: Optional list of LoRAs.
        denoising_strength: Lower values (0.25-0.40) preserve more of the original.
        backend, content_rating: Standard options.
    """
    result = _engine.inpaint_image(
        image_path=image_path,
        prompt=prompt,
        style=style or None,
        negative_prompt=negative_prompt or None,
        checkpoint=checkpoint or None,
        loras=loras or None,
        width=width or None,
        height=height or None,
        steps=steps or None,
        cfg=cfg or None,
        seed=None if seed < 0 else seed,
        denoising_strength=denoising_strength,
        backend=None if backend == "auto" else backend,
        content_rating=content_rating or "open",
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def inpaint_advanced(
    image_path: str,
    prompt: str,
    reference_image_path: str = "",
    flag_reference: str = "",
    mask_region: str = "church_tower",
    mask_path: str = "",
    style: str = "",
    negative_prompt: str = "",
    checkpoint: str = "",
    loras: list[dict[str, Any]] | None = None,
    denoising_strength: float = 0.55,
    ipadapter_weight: float = 0.85,
    use_controlnet_depth: bool = False,
    controlnet_depth_strength: float = 0.75,
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    cfg: float = 0,
    seed: int = -1,
    backend: str = "auto",
    content_rating: str = "open",
) -> str:
    """
    Advanced inpainting with optional IP-Adapter reference image.

    Best tool for adding new objects (flags, signs, text, etc.) while keeping
    the main subject as unchanged as possible.

    Args:
        image_path: Main image to edit.
        prompt: What to add/change (e.g. "add a large Irish flag on the church").
        reference_image_path: Optional reference image for IP-Adapter (e.g. a clean Irish flag photo).
        flag_reference: Shorthand — pass 'ireland' to use bundled Irish tricolor (auto-downloaded).
        mask_region: Auto-mask region to edit: top, top_third, top_two_thirds, full, or none.
        mask_path: Optional custom mask image (white=edit). Overrides mask_region.
        denoising_strength: 0.35–0.75 typical. Higher = more freedom to add new elements.
        ipadapter_weight: How strongly to follow the reference image (0.7–1.0).
        use_controlnet_depth: Enable depth control for better background separation.
    """
    result = _engine.inpaint_advanced(
        image_path=image_path,
        prompt=prompt,
        reference_image_path=reference_image_path or None,
        flag_reference=flag_reference,
        mask_region=mask_region,
        mask_path=mask_path or None,
        style=style or None,
        negative_prompt=negative_prompt or None,
        checkpoint=checkpoint or None,
        loras=loras or None,
        denoising_strength=denoising_strength,
        ipadapter_weight=ipadapter_weight,
        use_controlnet_depth=use_controlnet_depth,
        controlnet_depth_strength=controlnet_depth_strength,
        width=width or None,
        height=height or None,
        steps=steps or None,
        cfg=cfg or None,
        seed=None if seed < 0 else seed,
        backend=None if backend == "auto" else backend,
        content_rating=content_rating or "open",
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_video(
    prompt: str,
    mode: str = "t2v",
    style: str = "",
    negative_prompt: str = "",
    workflow_id: str = "",
    content_rating: str = "open",
    image_path: str = "",
    video_path: str = "",
    concat_source: bool = True,
    num_frames: int = 0,
    frame_rate: float = 0,
    lora_ids: str | list[str] = "",
    lora_bundle: str = "",
    use_painter_i2v: bool = False,
    motion_amplitude: float = 1.15,
    smooth_motion: bool = False,
) -> str:
    """
    Generate video via ComfyUI using saved Stability Matrix workflows.

    Args:
        prompt: Scene description.
        mode: t2v, i2v, or v2v (video extend from last frame).
        style: Optional image style for prompt prefix/negative defaults.
        negative_prompt: Override negative prompt for Wan text encode nodes.
        workflow_id: Short catalog id: t2v, i2v_5b, i2v_5b_painter, v2v_5b, v2v_5b_painter, i2v, i2v_wan21, i2v_gpu. Empty = auto. Do NOT pass the .json filename.
        content_rating: open (default) or sfw for optional safety negatives.
        image_path: Required for i2v — local path to the source image.
        video_path: Required for v2v — local path to source clip to extend.
        concat_source: For v2v — append continuation to source clip (default true).
        num_frames: Optional frame count override (e.g. 65 for ~4s at 16fps).
        frame_rate: Optional output fps override (e.g. 16).
        lora_ids: Wan video LoRA id(s): comma-separated string or list (face_naturalizer, …).
        lora_bundle: smooth_character | walk_cycle | cinematic_church | motion_boost — merged with lora_ids.
        use_painter_i2v: Inject PainterI2V node for motion_amplitude (or use workflow_id=i2v_5b_painter).
        motion_amplitude: PainterI2V strength 1.0–1.5 (default 1.15). Lower = subtler gait.
        smooth_motion: For i2v/v2v — gentler preset (lower amplitude, 12fps). On 16 GB prefer false + motion_amplitude 1.15–1.2.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    try:
        result = _engine.generate_video(
            prompt=prompt,
            mode=mode,
            style=style or None,
            negative_prompt=negative_prompt or None,
            workflow_id=workflow_id or None,
            content_rating=content_rating or "open",
            image_path=image_path or None,
            video_path=video_path or None,
            concat_source=concat_source,
            num_frames=num_frames or None,
            frame_rate=frame_rate or None,
            lora_ids=ids,
            lora_bundle=lora_bundle or "",
            use_painter_i2v=use_painter_i2v,
            motion_amplitude=motion_amplitude,
            smooth_motion=smooth_motion,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="generate_video")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def plan_storyboard_scene(
    script: str,
    hero_image: str = "",
    food_group: str = "anime",
    style: str = "",
    voice_instruction: str = "",
    project_name: str = "",
    frames_per_beat: int = 49,
    resolution: str = "832x480",
    frame_rate: float = 16.0,
    motion_amplitude: float = 1.1,
    include_lipsync: bool = False,
    include_audio_mux: bool = False,
    splice_clips: bool = True,
    fade_last_beat: bool = False,
) -> str:
    """
    Plan a full storyboard: hero Wan2GP I2V chain + MOSS dialogue + optional Infinitetalk + splice.

    Script: one beat per line — `action | dialogue` or action-only.
    Validated path: Rin walk/bow/stab (see STORYBOARD-QUICKSTART.md). Plan only — no GPU.
    """
    return json.dumps(
        _plan_storyboard_scene(
            script=script,
            hero_image=hero_image,
            food_group=food_group,
            style=style,
            voice_instruction=voice_instruction,
            project_name=project_name,
            frames_per_beat=frames_per_beat,
            resolution=resolution,
            frame_rate=frame_rate,
            motion_amplitude=motion_amplitude,
            include_lipsync=include_lipsync,
            include_audio_mux=include_audio_mux,
            splice_clips=splice_clips,
            fade_last_beat=fade_last_beat,
        ),
        indent=2,
    )


@mcp.tool()
def check_storyboard_readiness() -> str:
    """
    Check MOSS, Wan2GP hero I2V, GPU policy, and delivery project layout for storyboard work.

    Call before plan_storyboard_scene execute or Rin-style pipelines on 16 GB.
    """
    return json.dumps(_check_storyboard_readiness(_cfg), indent=2)


@mcp.tool()
def get_project_context(project_dir: str = "", backlog_limit: int = 20) -> str:
    """
    Cross-agent project briefing — read at session start (Cursor, OI, Jan).

    Returns current phase, active chapter, blockers, next actions, and recent agent_backlog.
    Truth for scenes stays in storyboard CSV; this file coordinates who did what.
    """
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    try:
        payload = _build_agent_briefing(root, backlog_limit=backlog_limit)
    except FileNotFoundError:
        return json.dumps(
            {
                "status": "not_initialized",
                "project_root": str(root),
                "hint": "Call init_project_context(project_dir=...) once per project.",
            },
            indent=2,
        )
    return json.dumps(payload, indent=2)


@mcp.tool()
def init_project_context(
    project_dir: str = "",
    project_name: str = "",
    book_title: str = "",
    active_chapter: int = 1,
) -> str:
    """Create logs/project_context.json + empty agent_backlog.jsonl for a delivery project."""
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    data = _init_project_context(
        root,
        project_name=project_name,
        book_title=book_title,
        active_chapter=active_chapter,
    )
    return json.dumps({"project_root": str(root), "context": data}, indent=2)


@mcp.tool()
def update_project_context(
    project_dir: str = "",
    agent: str = "cursor",
    phase: str = "",
    active_chapter: int = 0,
    summary: str = "",
    next_actions: list[str] | None = None,
    blockers: list[str] | None = None,
) -> str:
    """Update project snapshot after a session — phase, chapter, next steps, blockers."""
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    data = _update_project_context(
        root,
        agent=agent,
        phase=phase or None,
        active_chapter=active_chapter or None,
        next_actions=next_actions,
        blockers=blockers,
        summary=summary,
    )
    return json.dumps({"project_root": str(root), "context": data}, indent=2)


@mcp.tool()
def append_project_log(
    project_dir: str = "",
    agent: str = "cursor",
    action: str = "",
    summary: str = "",
    chapter: int = 0,
    scene_id: str = "",
    artifacts: list[str] | None = None,
) -> str:
    """Append one line to logs/agent_backlog.jsonl (what this agent just did)."""
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    entry = _append_project_log(
        root,
        agent=agent,
        action=action or "note",
        summary=summary,
        chapter=chapter or None,
        scene_id=scene_id,
        artifacts=artifacts,
    )
    return json.dumps(entry, indent=2)


@mcp.tool()
def log_image_prompt(
    prompt_positive: str,
    prompt_negative: str = "",
    platform: str = "",
    style: str = "",
    scene_id: str = "",
    chapter: int = 0,
    source_image: str = "",
    notes: str = "",
    agent: str = "jan",
    project_dir: str = "",
) -> str:
    """
    Append a prompt-only or brainstorm entry to logs/prompt_log.jsonl.

    Jan Prompt Lab: call after every Platform/Positive/Negative reply (no GPU).
    Links to storyboard scene_id when known.
    """
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None) if project_dir else _delivery_project_root()
    if root is None:
        raise ValueError("No project_dir and outputs.delivery not set in config.yaml")
    row = _log_prompt_only(
        root,
        agent=agent,
        scene_id=scene_id,
        platform=platform,
        style=style,
        prompt_positive=prompt_positive,
        prompt_negative=prompt_negative,
        source_image=source_image,
        notes=notes,
        chapter=chapter or None,
    )
    _append_project_log(
        root,
        agent=agent,
        action="log_image_prompt",
        summary=f"Prompt logged ({platform or style or 'text'})",
        chapter=chapter or None,
        scene_id=scene_id,
        artifacts=[str(_prompt_log_path(root))],
    )
    plog = _prompt_log_path(root)
    return json.dumps({"project_root": str(root), "prompt_log": str(plog), "entry": row}, indent=2)


@mcp.tool()
def list_image_prompt_log(
    project_dir: str = "",
    limit: int = 30,
    scene_id: str = "",
    style: str = "",
    kind: str = "",
) -> str:
    """Read recent image/video prompts from logs/prompt_log.jsonl."""
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None) if project_dir else _delivery_project_root()
    if root is None:
        raise ValueError("No project_dir and outputs.delivery not set in config.yaml")
    rows = _read_prompt_log(root, limit=limit, scene_id=scene_id, style=style, kind=kind)
    return json.dumps(
        {
            "project_root": str(root),
            "log": str(root / "logs" / "prompt_log.jsonl"),
            "count": len(rows),
            "entries": rows,
        },
        indent=2,
    )


@mcp.tool()
def init_storyboard_sheet(chapter: int = 1, title: str = "", project_dir: str = "") -> str:
    """
    Create storyboard/chXX_storyboard.csv for a VN chapter (Excel-friendly).

    One row per scene: still, dialogue, video, narration, etc. Asset paths are pre-filled
    from scene_id so generated files land in predictable locations.
    """
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    path = _init_chapter_sheet(root, chapter=chapter, title=title)
    return json.dumps({"project_root": str(root), "sheet": str(path), "chapter": chapter}, indent=2)


@mcp.tool()
def check_storyboard_sheet(chapter: int = 1, project_dir: str = "", strict: bool = False) -> str:
    """Validate chapter CSV — duplicate ids, missing approved assets, row warnings."""
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    path = _storyboard_sheet_path(root, chapter)
    return json.dumps(_validate_storyboard_sheet(root, path, strict=strict), indent=2)


@mcp.tool()
def list_storyboard_generation_queue(chapter: int = 1, project_dir: str = "") -> str:
    """
    Rows with prompts/actions ready for MCP generate_image / generate_video_hero / generate_audio.

    Agent: fill prompt_positive in the sheet first, set status=prompt_ready, then work the queue.
    """
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    path = _storyboard_sheet_path(root, chapter)
    rows, meta = _load_storyboard_sheet(path)
    return json.dumps(
        {
            "sheet": str(path),
            "meta": meta,
            "queue": _rows_needing_generation(rows),
        },
        indent=2,
    )


@mcp.tool()
def export_renpy_skeleton(chapter: int = 1, project_dir: str = "", game_name: str = "vn_game") -> str:
    """
    Export Ren'Py label + image definition skeleton from the chapter storyboard CSV.

    Writes renpy/generated/chXX_script.rpy — review before shipping.
    """
    from studio.storyboard_cli import resolve_project_dir

    root = resolve_project_dir(project_dir or None)
    path = _storyboard_sheet_path(root, chapter)
    return json.dumps(
        _export_renpy_skeleton(root, path, chapter=chapter, game_name=game_name),
        indent=2,
    )


@mcp.tool()
def plan_scene_sequence(
    script: str,
    food_group: str = "anime",
    hero_image: str = "",
    style: str = "",
    frames_per_beat: int = 49,
    frame_rate: float = 16.0,
    use_painter: bool = True,
    motion_amplitude: float = 1.15,
) -> str:
    """
    Preview a multi-beat storyboard from a short script (no GPU).

    Script format: one beat per line; optional leading numbers or dashes.
    With hero_image: first beat is I2V, later beats V2V extend. Without: first beat T2I.
    """
    return json.dumps(
        plan_scene_sequence(
            script=script,
            food_group=food_group,
            hero_image=hero_image,
            style=style,
            frames_per_beat=frames_per_beat,
            frame_rate=frame_rate,
            use_painter=use_painter,
            motion_amplitude=motion_amplitude,
        ),
        indent=2,
    )


@mcp.tool()
def generate_scene_sequence(
    script: str,
    food_group: str = "anime",
    hero_image: str = "",
    style: str = "",
    frames_per_beat: int = 49,
    frame_rate: float = 16.0,
    use_painter: bool = True,
    motion_amplitude: float = 1.15,
    execute: bool = False,
) -> str:
    """
    Plan or run a linked clip sequence from a short script.

    Args:
        execute: False = plan only (default). True = run beats sequentially on GPU.
    """
    plan = plan_scene_sequence(
        script=script,
        food_group=food_group,
        hero_image=hero_image,
        style=style,
        frames_per_beat=frames_per_beat,
        frame_rate=frame_rate,
        use_painter=use_painter,
        motion_amplitude=motion_amplitude,
    )
    if not execute:
        return json.dumps({"executed": False, "plan": plan}, indent=2)
    try:
        result = _engine.execute_scene_sequence(plan)
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="generate_scene_sequence")
        err["ok"] = False
        err["plan"] = plan
        return json.dumps(err, indent=2)


@mcp.tool()
def check_moss_assets() -> str:
    """Check MOSS-TTS custom node install and downloaded models (speech, SFX, voice design)."""
    status = _check_moss_assets_status(_cfg)
    comfy_url = _comfy_url()
    try:
        node_check = check_node_types(cfg=_cfg, comfy_url=comfy_url, required=set(MOSS_NODES))
        status["comfyui_nodes"] = node_check
    except Exception as exc:
        status["comfyui_nodes"] = {"ready": False, "error": str(exc)}
    return json.dumps(status, indent=2)


@mcp.tool()
def download_moss_assets(
    model_ids: str = "",
    force: bool = False,
) -> str:
    """
    Download MOSS-TTS models into ComfyUI/models/moss-tts/.

    Args:
        model_ids: Comma-separated ids: audio_tokenizer, tts_local, sound_effect, voice_generator. Empty = all.
        force: Re-download even when present.
    """
    ids = [s.strip() for s in model_ids.split(",") if s.strip()] or None
    results = download_moss_models(_cfg, model_ids=ids, force=force)
    status = _check_moss_assets_status(_cfg)
    return json.dumps({"downloads": results, "status": status}, indent=2)


@mcp.tool()
def check_gpu_backend() -> str:
    """
    Snapshot GPU backend policy: ComfyUI vs Wan2GP ports, MCP lock, VRAM, allowed backends.

    Call before generate_video, generate_audio, or generate_video_hero — especially for
    offline agents (Jan, LM Studio) that cannot rely on Cursor-side enforcement alone.
    """
    status = inspect_gpu_backend(_cfg, comfyui_running=_engine.comfy.is_running())
    return json.dumps(status, indent=2)


@mcp.tool()
def release_gpu_lock(holder: str = "") -> str:
    """
    Clear the MCP GPU lock file (outputs/.gpu_backend.lock).

    Args:
        holder: Optional — only release if lock is held by comfyui or wan2gp. Empty = force clear.
    """
    h = holder.strip().lower() or None
    if h and h not in {"comfyui", "wan2gp"}:
        return json.dumps({"released": False, "error": "holder must be comfyui, wan2gp, or empty"}, indent=2)
    result = _release_gpu_lock(_cfg, h)  # type: ignore[arg-type]
    return json.dumps(result, indent=2)


@mcp.tool()
def check_wan2gp_runtime() -> str:
    """Check Wan2GP assets, MCP reachability, and whether hero I2V is allowed under gpu_backend policy."""
    return json.dumps(
        _check_wan2gp_runtime(_cfg, comfyui_running=_engine.comfy.is_running()),
        indent=2,
    )


@mcp.tool()
def plan_wan2gp_job(
    prompt: str,
    image_path: str,
    negative_prompt: str = "",
    video_length: int = 49,
    resolution: str = "832x480",
) -> str:
    """Preview Wan2GP hero I2V settings (no GPU). Use generate_video_hero to run."""
    return json.dumps(
        _plan_wan2gp_job(
            prompt=prompt,
            image_path=image_path,
            negative_prompt=negative_prompt,
            video_length=video_length,
            resolution=resolution,
        ),
        indent=2,
    )


@mcp.tool()
def generate_video_hero(
    prompt: str,
    image_path: str,
    negative_prompt: str = "",
    video_length: int = 49,
    resolution: str = "832x480",
    seed: int = -1,
    motion_amplitude: float = 1.05,
) -> str:
    """
    Hero-quality I2V via Wan2GP Enhanced Lightning v2 (outside ComfyUI).

    Requires: ComfyUI stopped, Wan2GP Gradio UI stopped, Lightning v2 weights installed.
    Auto-starts Wan2GP MCP on gpu_backend.wan2gp_mcp_port (default 7867) when configured.

    Args:
        prompt: Motion/scene description (e.g. Japanese bow, subtle forward lean).
        image_path: Local path to source still (kitsune portrait, etc.).
        negative_prompt: Optional negatives.
        video_length: Frame count (default 49 ≈ 3s at 16fps).
        resolution: e.g. 832x480.
        seed: -1 = random.
        motion_amplitude: Wan2GP motion strength (default 1.05 for subtle bow).
    """
    try:
        result = _engine.generate_video_hero(
            prompt=prompt,
            image_path=image_path,
            negative_prompt=negative_prompt,
            video_length=video_length,
            resolution=resolution,
            seed=seed,
            motion_amplitude=motion_amplitude,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="generate_video_hero")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def check_wan2gp_assets() -> str:
    """Check Wan2GP I2V checkpoint files (hero-quality video outside ComfyUI MCP path)."""
    return json.dumps(_check_wan2gp_assets_status(_cfg), indent=2)


@mcp.tool()
def download_wan2gp_assets(force: bool = False) -> str:
    """Download Wan2GP Enhanced Lightning v2 I2V weights into Wan2GP/ckpts/."""
    results = download_wan2gp_lightning(_cfg, force=force)
    status = _check_wan2gp_assets_status(_cfg)
    return json.dumps({"downloads": results, "status": status}, indent=2)


@mcp.tool()
def list_media_paths() -> str:
    """Return canonical local folders for MCP, ComfyUI, Wan2GP image/audio/video outputs."""
    return json.dumps(media_paths(_cfg), indent=2)


@mcp.tool()
def generate_audio(
    mode: str = "speech",
    text: str = "",
    prompt: str = "",
    instruction: str = "",
    language: str = "en",
    duration_seconds: float = 0.0,
    seed: int = -1,
    filename_prefix: str = "",
) -> str:
    """
    Generate speech or sound effects via MOSS-TTS in ComfyUI (no reference recording).

    Args:
        mode: speech (default TTS), sound_effect, or voice_design.
        text: Words to speak (speech / voice_design).
        prompt: Sound description for sound_effect (alias: use text if prompt empty).
        instruction: Voice description for voice_design (e.g. warm female narrator, mid-30s).
        language: auto, en, zh, ja, ko for speech/voice_design.
        duration_seconds: SFX length 0.5–60 (sound_effect, default 5 if 0). Voice design: optional
            target seconds via MOSS tokens field (12.5 tokens/s); 0 = auto from text length.
        seed: Random seed (-1 = random).
        filename_prefix: ComfyUI SaveAudio prefix under output/audio/.
    """
    try:
        result = _engine.generate_audio(
            mode=mode,
            text=text,
            prompt=prompt,
            instruction=instruction,
            language=language,
            duration_seconds=duration_seconds,
            seed=None if seed < 0 else seed,
            filename_prefix=filename_prefix or "",
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="generate_audio")
        err["ok"] = False
        return json.dumps(err, indent=2)


MCP_TOOL_COUNT = len(mcp._tool_manager._tools)

if __name__ == "__main__":
    mcp.run()

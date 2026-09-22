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

from mcp.server.fastmcp import FastMCP, Image

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
from studio.hunyuan_assets import check_all_hunyuan_assets, download_missing as download_hunyuan_missing
from studio.wan_video_loras import (
    check_wan_video_loras as _check_wan_video_loras_status,
    download_wan_video_loras as _fetch_wan_video_loras,
    suggest_wan_action_lora as _suggest_wan_action_lora,
)
from studio.nsfw_image_loras import (
    NSFW_IMAGE_LORA_BUNDLES,
    NSFW_IMAGE_LORAS,
    check_nsfw_image_loras as _check_nsfw_image_loras_status,
    download_nsfw_image_loras as _fetch_nsfw_image_loras,
    list_nsfw_image_loras_for_style,
    resolve_nsfw_lora_list,
)
from studio.character_loras import (
    check_character_loras_on_disk as _check_character_loras_on_disk,
    list_baked_in_characters as _list_baked_in_characters,
    list_character_loras as _list_character_loras,
    list_character_mesh_assets as _list_character_mesh_assets,
    lookup_character_identity as _lookup_character_identity,
    resolve_character_loras as _resolve_character_loras,
)
from studio.doc_reader import (
    append_lesson as _append_lesson,
    list_studio_docs as _list_studio_docs,
    read_studio_doc as _read_studio_doc,
    search_studio_docs as _search_studio_docs,
)
from studio.asset_naming import suggest_asset_name as _suggest_asset_name
from studio.web_fetch import fetch_web_documentation as _fetch_web_documentation
from studio.set_mesh_assets import (
    list_set_mesh_assets as _list_set_mesh_assets,
    list_solid_strip_maps as _list_solid_strip_maps,
)
from studio.style_lanes import resolve_style_lane as _resolve_style_lane
from studio.chapter_phonetic import rewrite_chapter_phonetic as _rewrite_chapter_phonetic
from studio.style_assets import (
    check_all_style_assets,
    check_style_assets as _check_style_assets_impl,
    download_style_assets as fetch_style_assets,
)
from studio.moss_assets import (
    MOSS_NODES,
    check_moss_assets as _check_moss_assets_status,
    download_moss_models,
    list_source_images as _list_source_images,
    media_paths,
)
from studio.delivery_media import (
    copy_delivery_media as _copy_delivery_media,
    list_delivery_media as _list_delivery_media,
    media_root_info as _media_root_info,
    move_delivery_media as _move_delivery_media,
    open_delivery_in_explorer as _open_delivery_in_explorer,
    recycle_delivery_media as _recycle_delivery_media,
    rename_delivery_media as _rename_delivery_media,
    view_delivery_image_payload as _view_delivery_image_payload,
    view_delivery_video_frame_payload as _view_delivery_video_frame_payload,
)
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
from studio.nari_ollama import (
    maybe_unload_nari_for_audio as _maybe_unload_nari_for_audio,
    maybe_unload_nari_for_hero as _maybe_unload_nari_for_hero,
    maybe_unload_nari_for_video as _maybe_unload_nari_for_video,
    nari_ollama_status as _nari_ollama_status,
    unload_nari_models as _unload_nari_models,
)
from studio.forge_backend import (
    generate_image_forge as _generate_image_forge,
    inspect_forge_backend,
    refine_image_forge as _refine_image_forge,
    switch_stills_backend as _switch_stills_backend,
)
from studio.kokoro_client import (
    inspect_kokoro_backend,
    list_kokoro_voices as _list_kokoro_voices,
    synthesize_kokoro,
)
from studio.video_post import (
    interpolate_video as _interpolate_video,
    polish_wan_best as _polish_wan_best,
    polish_wan_video as _polish_wan_video,
)
from studio.wan_preflight import (
    check_ebsynth as _check_ebsynth,
    check_wan_prompt as _check_wan_prompt,
    extract_chain_lastframe as _extract_chain_lastframe,
    gate_i2v_clip as _gate_i2v_clip,
    plan_wan_beat as _plan_wan_beat,
    recommend_polish as _recommend_polish,
)
from studio.video_upscale import (
    check_local_post as _check_local_post,
    upscale_video_local as _upscale_video_local,
)
from studio.video_splice import (
    concat_video_clips as _concat_video_clips,
    splice_crossfade_loop as _splice_crossfade_loop,
    splice_pingpong as _splice_pingpong,
    splice_pose_matched_loop as _splice_pose_matched_loop,
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
        "Call get_generation_context first (brief=true by default) — hardware_profile and generation_limits. "
        "Use brief=false only for full setup audits (slow). "
        "(GPU VRAM caps). Stay within generation_limits unless the user explicitly asks for more. "
        "New users: call get_onboarding_context first — guided tiers, VRAM routing, install checklist (onboarding/). "
        "Not a one-click installer; AI-assisted ComfyUI workflow. "
        "≥24 GB VRAM: ComfyUI only, do not offer Wan2GP. ≤16 GB: Wan2GP only if user explicitly wants hero/lip sync. "
        "Prefer prompt quality (face, hands, anatomy) over max resolution. "
        "Use style ids from the catalog (anime, ilustmix, fantasy_prime, homochi, n4mik4, juggernaut, pony, …). "
        "Four art food groups: anime, fantasy, cyberpunk, photoreal — pass food_group= to edit_image. "
        "Each style has an architecture (sd15, sdxl, pony_sdxl, flux2_klein) — see get_generation_context. "
        "Image edits: setup_image_editing() then edit_image(image_path, instruction, food_group=...). "
        "Before first image on a new PC: check style_readiness in get_generation_context; "
        "Flux2: check_style_assets / download_style_assets(style='miracle_nsfw'). "
        "Aliases work: 'illustrious'→anime, 'fantasyprime'→fantasy_prime, 'ragnarok'→juggernaut. "
        "Pass checkpoint= to override. For video: call check_comfyui_dependencies(workflow_id) first; "
        "if missing nodes, call install_comfyui_dependencies then restart ComfyUI on the generation host. "
        "Use generate_video(mode=t2v|i2v|v2v, workflow_id=t2v|i2v_5b|i2v_5b_painter|v2v_5b|v2v_5b_painter|i2v|flf2v|i2v_gpu) — short ids only. "
        "CRITICAL: mode=v2v / v2v_5b* = EXTEND from last frame only — does NOT clean/re-denoise an existing clip. "
        "True latent clean = catalog workflow_id=v2v_upscale (Wan 1.3B denoise ~0.1; mute RIFE). Not wired into generate_video yet — ComfyUI UI. "
        "Default I2V: i2v_5b (Wan 2.2 TI2V-5B, often censored). User asks for 14B / NSFW motion → "
        "generate_video(mode=i2v, workflow_id=i2v) = Wan 2.2 I2V-A14B MoE HIGH+LOW — NOT generate_video_hero, NOT i2v_5b. "
        "FLF2V: workflow_id=flf2v + image_path + end_image_path; prefer ~21f for hard contact / dual-face. "
        "Never map '14B' to Wan2GP / generate_video_hero. "
        "I2V identity: short motion-only prompts; do not re-describe the still; gate_i2v_clip after gen. "
        "No i2v_5b_painter / PainterI2V when the user needs face/body lock (BJ, portraits) — use workflow_id=i2v. "
        "MoE LoRAs: stack HIGH on high expert + LOW on low expert (Lightning pair + at most one action pair). "
        "Bundles: female_orgasm, lightning_i2v, orgasm_lightning, oral_insertion, oral_deepthroat, ultimate_deepthroat, missionary_sex, pov_insertion, doggy_sex, facial_cum. "
        "Never orgasm HIGH alone on i2v. Keepers: moe_preset=quality (default) or omit; draft=True / moe_preset=fast = Lightning only. "
        "Wan action-LoRA checklist (REQUIRED before NSFW I2V keepers): "
        "(1) plan_wan_beat / resolve_wan_action_loras(prompt=…, beat_hint=oral|doggy|…) — pick the action bundle; "
        "(2) check_wan_prompt(prompt=…); "
        "(3) if ready=false → download_wan_video_loras(bundle=…); "
        "(4) generate_video(..., lora_bundle=<id>, moe_preset=quality); "
        "(5) gate_i2v_clip → human keep → extract_chain_lastframe only if chaining. "
        "Map: BJ tip-suck/soft bob→oral_insertion; deepthroat/bury→oral_deepthroat; doggy→doggy_sex; tip→bury→pov_insertion; "
        "already-in thrusts→missionary_sex; facial shoot→facial_cum. "
        "Do not generate hard contact / head-bob / insertion from prompt alone when a bundle exists. "
        "Polish: recommend_polish first; Saloon/no-RIFE: polish_wan_best(skip_interpolate=true) SeedVR-only — ALWAYS A/B vs original (SS02 2026-08-20 SeedVR lost to master). "
        "check_ebsynth before claiming EBSynth restore. "
        "Wan NSFW: never prompt full penis exit; partial withdraw only; negate deflating/disappearing shaft. "
        "Never prompt female 'cum' — use orgasm/squirting/juices. One Comfy job at a time; free VRAM between heavy runs. "
        "If ok=false do not claim success; after success, verify identity vs source still. "
        "workflow_id=i2v_5b_painter or use_painter_i2v=true for PainterI2V motion (5B path only). "
        "Optional Wan video LoRAs: resolve_wan_action_loras / check_wan_video_loras / download_wan_video_loras(bundle=…). "
        "generate_video: lora_ids / lora_bundle / lora_weights={id:w} and/or loras=[{file,weight,branch}]; "
        "moe_preset=quality|fast; draft=True for Lightning probes. "
        "motion_amplitude is PainterI2V-only (5B) — ignored on MoE i2v. "
        "smooth_motion=true → quality MoE + may inject smooth_character (face+camera), not a motion smoother. "
        "Call check_wan_assets / download_wan_assets for Wan base models. "
        "HunyuanVideo 1.5: check_hunyuan_assets / download_hunyuan_assets (assets only; generate_video routing TBD). "
        "Audio (MOSS-TTS): check_moss_assets → download_moss_assets → generate_audio(mode=speech|sound_effect|voice_design). "
        "Kokoro book TTS (CPU :8090): check_kokoro_backend → generate_speech_kokoro — no GPU lock (AUDIO-KOKORO.md). "
        "Labor split: GENERATION_HOST/GenerationHost (RTX 5090 CUDA) = GPU diffusion (generate_image, Forge refine, Wan video); "
        "main rig (7900X + 5060 Ti) = CPU-heavy work + local polish (ffmpeg/splice/interp, file ops, "
        "polish_wan_video / AnimeSharp). Generate on GenerationHost; polish and package locally. "
        "Post-clip (main rig 5060 Ti / 7900X, not Jan): check_local_post → recommend_polish → "
        "polish_wan_best (Saloon: skip_interpolate SeedVR-only; else RIFE→SeedVR2) or "
        "interpolate_video → upscale_video_local / polish_wan_video; "
        "splice via concat_video_clips / splice_pingpong / splice_pose_matched_loop / "
        "splice_crossfade_loop. Generate Wan on generation-host; polish locally. "
        "GPU policy: call check_gpu_backend before generate_video / generate_audio / generate_video_hero. "
        "Comfybox Forge (:7860) exclusive with ComfyUI — switch_stills_backend then refine_image_forge / generate_image_forge (COMFYBOX-FORGE.md). "
        "Draft I2V: generate_video(mode=i2v, workflow_id=i2v_5b). "
        "Wan2GP hero (generate_video_hero) ONLY if user explicitly says hero / Wan2GP / lip-sync — then stop remote ComfyUI via ssh gpu_backend.sh, not Windows Stability Matrix. "
        "Never run ComfyUI video and Wan2GP UI together. "
        "Offline agents (Jan, Pi, LM Studio / EdgeVoice): check_gpu_backend is mandatory — conflicts return gpu_backend_conflict. "
        "Source stills: call list_source_images(query=...) before inventing image_path. "
        "Never rewrite C:\\Users\\... to D:\\Users\\.... Never guess delivery/Video or delivery/Images as inputs. "
        "Common drops: Desktop\\New Images and delivery\\User Import. Pass the exact path returned. "
        "To SEE pixels: list_delivery_media then view_delivery_image / view_delivery_video_frame "
        "(generate_* returns paths only — viewing is separate). "
        "Video outputs: generate_video lands under delivery Video/; character projects promote into "
        "Video/<Character>/ only (e.g. Video/Frieren/). No nested quarantine/review trees — fails go to Recycle Bin. "
        "Trust saved_files paths; never invent success when ok=false. "
        "Never use web search for image generation — call generate_image. "
        "Media output paths: get_generation_context.media_paths or list_media_paths. "
        "For inpaint_advanced (flags, reference objects): setup_ip_adapter or "
        "install_ip_adapter_dependencies + download_ip_adapter_assets — then restart ComfyUI."
    ),
)

_cfg = load_config()
_catalog = StyleCatalog(catalog_path(_cfg), _cfg)
_engine = GenerationEngine(_cfg, _catalog)
print(
    f"[stability-studio] ComfyUI {_cfg.get('comfyui', {}).get('url')} "
    f"reachable={_engine.comfy.is_running()}",
    file=sys.stderr,
    flush=True,
)


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


def _parse_lora_weights_arg(value: Any = None) -> dict[str, float] | None:
    """Accept dict or JSON object of catalog_id → weight (split HIGH/LOW)."""
    if value is None or value == "" or value == {}:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, dict):
        return None
    out: dict[str, float] = {}
    for key, raw in value.items():
        kid = str(key).strip().lower()
        if not kid:
            continue
        try:
            out[kid] = float(raw)
        except (TypeError, ValueError):
            continue
    return out or None


def _parse_video_loras_arg(value: Any = None) -> list[dict[str, Any]] | None:
    """Accept list[{file|id, weight, branch}] or JSON string — MoE pass-through."""
    if value is None or value == "" or value == []:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, list):
        return None
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        file_name = str(item.get("file") or item.get("name") or "").strip()
        lid = str(item.get("id") or "").strip()
        if not file_name and lid:
            try:
                from studio.wan_video_loras import resolve_lora_entry

                entry = resolve_lora_entry(lid)
                file_name = str(entry["filename"])
                lid = str(entry["id"])
                branch = str(item.get("branch") or entry.get("branch") or "both")
                weight = float(item.get("weight", entry.get("default_weight", 0.6)))
            except Exception:
                continue
        else:
            branch = str(item.get("branch") or "").strip() or "both"
            try:
                weight = float(item.get("weight", 0.6))
            except (TypeError, ValueError):
                weight = 0.6
        if not file_name:
            continue
        row: dict[str, Any] = {"file": file_name, "weight": weight, "branch": branch.lower()}
        if lid:
            row["id"] = lid
        out.append(row)
    return out or None


def _resolve_generate_video_loras(
    *,
    lora_ids: list[str] | None,
    lora_bundle: str,
    lora_weights: dict[str, float] | None,
    loras: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Merge catalog ids/bundle (+ optional weights) with explicit loras= pass-through."""
    from studio.wan_video_loras import resolve_lora_list

    catalog: list[dict[str, Any]] = []
    if lora_ids or lora_bundle or lora_weights:
        catalog = resolve_lora_list(lora_ids, bundle=lora_bundle or "", weights=lora_weights)
    custom = loras or []
    if not catalog and not custom:
        return None
    if not custom:
        return catalog
    if not catalog:
        return custom
    # Catalog first; custom entries override same filename / id.
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in catalog + custom:
        key = str(item.get("id") or item.get("file") or "").lower()
        if not key:
            continue
        if key not in by_key:
            order.append(key)
        by_key[key] = item
    return [by_key[k] for k in order]


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
def get_generation_context(brief: bool = True) -> str:
    """
    Return styles, GPU limits, and backend status for generation.

    Args:
        brief: True (default) — fast essentials for Jan/Cursor (~1–3s). False — full
            asset scans + ComfyUI node readiness (slow; use for setup audits only).

    Brief mode is enough before generate_image. Call check_style_assets(style=...)
    when you need one style's file manifest.
    """
    from studio.comfy_deps import clear_installed_node_types_cache

    comfy_url = _comfy_url()
    ctx: dict[str, Any] = (
        _catalog.get_generation_context_brief()
        if brief
        else _catalog.get_generation_context()
    )
    if brief:
        ctx["mode"] = "brief"
    ctx["backend_status"] = _engine.backend_status()
    ctx.update(_engine.hardware_context())
    ctx["art_food_groups"] = _catalog.art_food_groups or ART_FOOD_GROUPS
    ctx["gpu_backend_policy"] = gpu_backend_policy_for_context(_cfg)
    ctx["forge"] = inspect_forge_backend(_cfg)
    ctx["kokoro"] = inspect_kokoro_backend(_cfg)
    ctx["stills_backends"] = {
        "mcp_generate_image": "comfyui",
        "adetailer_hires_stills": "forge_generation-host",
        "host_policy": (
            "All create/refine/Wan on GenerationHost 5090 first. Windows Forge/Comfy only if the "
            "user explicitly says so, or GenerationHost GPU is cooking a long video/batch."
        ),
        "workflow": (
            "generate_image (GenerationHost ComfyUI) → switch_stills_backend(forge) on GenerationHost → "
            "refine_image_forge → switch_stills_backend(comfy) → "
            "generate_video(workflow_id=i2v) for NSFW/keepers"
        ),
        "note": (
            "ComfyUI: generate_image / edit_image / generate_video on GenerationHost. "
            "Forge: GenerationHost :7860 via switch_stills_backend + refine_image_forge "
            "(ADetailer/hires) — not Windows Forge by default. Exclusive GPU. "
            "Default keeper I2V: workflow_id=i2v (Wan 2.2 14B MoE). Draft/SFW only: i2v_5b. "
            "See COMFYBOX-FORGE.md + LESSONS-WAN-I2V.md."
        ),
        "tools": [
            "check_forge_backend",
            "switch_stills_backend",
            "generate_image_forge",
            "refine_image_forge",
        ],
        "exiled_styles": ["fantasy_prime", "homochi", "anime", "ilustmix", "n4mik4", "juggernaut", "pony"],
    }
    ctx["offline_agents"] = {
        "jan": {
            "assistant": "Studio Copilot",
            "mcp_server": "stability-studio",
            "forbid": ["web_search_for_generation"],
            "before_generate": ["get_generation_context", "check_gpu_backend (video/audio/hero)"],
            "styles": "Use catalog ids: fantasy_prime, homochi, ilustmix, anime, juggernaut, pony, n4mik4 — not raw filenames.",
        },
        "pi_studio_edge": {
            "personas": {"myra": "room (Ollama)", "jan": "studio via Windows Jan MCP or direct ComfyUI"},
            "generation_route": "comfyui preferred for voice reliability; jan_mcp for orchestration",
            "comfyui_url": (_cfg.get("comfyui") or {}).get("url"),
            "default_styles": ["anime", "fantasy_prime", "homochi", "ilustmix"],
        },
    }
    ctx["media_paths"] = media_paths(_cfg)
    ver = build_info()
    ver["mcp_tool_count"] = MCP_TOOL_COUNT
    ctx["studio_version"] = ver
    ctx["restart_guide"] = "RESTART-GUIDE.md — ComfyUI vs MCP vs parallel GPU jobs"
    ctx["nsfw_image_loras"] = _check_nsfw_image_loras_status(_cfg, comfy_url=comfy_url)

    if not brief:
        clear_installed_node_types_cache(comfy_url)
        ctx["wan_video_assets"] = check_all_video_assets(_cfg)
        ctx["wan_video_loras"] = _check_wan_video_loras_status(_cfg)
        ctx["ip_adapter_readiness"] = _check_ip_adapter_assets(_cfg, include_optional=False)
        ctx["ip_adapter_dependencies"] = _check_ip_adapter_dependencies(
            _cfg, comfy_url, include_depth=False
        )
        ctx["image_editing_readiness"] = _check_image_editing_readiness(_cfg, comfy_url)
        ctx["face_detail_readiness"] = _check_face_detail_dependencies(_cfg, comfy_url)
        ctx["moss_audio"] = _check_moss_assets_status(_cfg)
        ctx["wan2gp_assets"] = _check_wan2gp_assets_status(_cfg)
        ctx["pose_control_readiness"] = _check_pose_control_readiness(_cfg, comfy_url)
        ctx["mode"] = "full"

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
def check_hunyuan_assets(workflow_id: str = "") -> str:
    """
    Check installed vs missing models for HunyuanVideo 1.5 workflows (T2V / I2V / optional SR).

    Assets only — generate_video routing not wired yet; use ComfyUI template workflows until then.

    Args:
        workflow_id: Catalog id (hunyuan_t2v, hunyuan_i2v, hunyuan_sr). Empty = all workflows + routing note.
    """
    if workflow_id:
        from studio.hunyuan_assets import check_workflow_assets

        return json.dumps(check_workflow_assets(_cfg, workflow_id), indent=2)
    return json.dumps(check_all_hunyuan_assets(_cfg), indent=2)


@mcp.tool()
def download_hunyuan_assets(
    workflow_id: str = "hunyuan_t2v",
    include_large: bool = False,
    include_optional: bool = False,
    force: bool = False,
) -> str:
    """
    Download missing HunyuanVideo 1.5 models from Hugging Face into Stability Matrix folders.

    Args:
        workflow_id: hunyuan_t2v (default), hunyuan_i2v, hunyuan_sr (optional 1080p SR).
        include_large: If true, also download multi-GB diffusion / text encoder files.
        include_optional: If true, also download optional assets (e.g. hunyuan_sr 1080p model).
        force: Re-download even when files exist.
    """
    results = download_hunyuan_missing(
        _cfg,
        workflow_id,
        include_large=include_large,
        include_optional=include_optional,
        force=force,
    )
    summary = check_all_hunyuan_assets(_cfg)
    return json.dumps({"downloads": results, "summary": summary["summary"]}, indent=2)


@mcp.tool()
def check_wan_video_loras(lora_ids: str | list[str] = "") -> str:
    """
    Check optional Wan 2.2 video LoRAs (motion, face, lighting, camera, action pairs).

    Prefer resolve_wan_action_loras(prompt=…) first on NSFW beats — it returns the
    checklist + recommended bundle, then use this tool / download_wan_video_loras to
    confirm files are on disk before generate_video.

    Args:
        lora_ids: Catalog id(s): comma-separated string or list (e.g. face_naturalizer,
            oral_insertion_i2v_high). Empty = all.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    return json.dumps(_check_wan_video_loras_status(_cfg, ids), indent=2)


@mcp.tool()
def resolve_wan_action_loras(prompt: str = "", beat_hint: str = "") -> str:
    """
    Preflight checklist: pick the correct Wan MoE *action* LoRA bundle for a beat.

    Call this BEFORE generate_video for NSFW sex/oral/doggy/insert keepers. Returns
    recommended lora_bundle, install ready/missing, and the agent checklist.

    Beat map: oral/BJ tip-suck/soft bob → oral_insertion; deepthroat/throat/bury → oral_deepthroat;
    doggy → doggy_sex; tip→bury → pov_insertion; already-in thrusts → missionary_sex; facial → facial_cum.

    Args:
        prompt: Planned I2V motion prompt (short).
        beat_hint: Optional override — free text or bundle id
            (oral_insertion|oral_deepthroat|doggy_sex|pov_insertion|missionary_sex|facial_cum).
    """
    return json.dumps(
        _suggest_wan_action_lora(prompt or "", beat_hint=beat_hint or "", cfg=_cfg),
        indent=2,
    )


@mcp.tool()
def check_ebsynth() -> str:
    """Verify jamriska ebsynth.exe is installed (real PatchMatch, not OpenCV paste)."""
    return json.dumps(_check_ebsynth(), indent=2)


@mcp.tool()
def check_wan_prompt(
    prompt: str,
    negative_prompt: str = "",
    framing: str = "",
    beat_hint: str = "",
) -> str:
    """
    Hygiene scan for Wan I2V prompts (camera words, multi-verb, female cum, full exit,
    head-still traps, eye/mouth tags on rear views). Fix high issues before keepers.
    """
    return json.dumps(
        _check_wan_prompt(
            prompt,
            negative_prompt=negative_prompt or "",
            framing=framing or "",
            beat_hint=beat_hint or "",
        ),
        indent=2,
    )


@mcp.tool()
def plan_wan_beat(
    beat_hint: str = "",
    still_notes: str = "",
    prompt: str = "",
    hard_contact: bool = False,
    dual_face: bool = False,
) -> str:
    """
    Map tip-vs-already-in / pose family → LoRA bundle + frames + one-verb template.
    Call before generate_video for NSFW action keepers (with resolve_wan_action_loras).
    """
    return json.dumps(
        _plan_wan_beat(
            beat_hint=beat_hint or "",
            still_notes=still_notes or "",
            prompt=prompt or "",
            hard_contact=hard_contact,
            dual_face=dual_face,
            cfg=_cfg,
        ),
        indent=2,
    )


@mcp.tool()
def gate_i2v_clip(
    video_path: str,
    start_image_path: str = "",
    work_dir: str = "",
) -> str:
    """
    Gate f0 / mid / last vs optional start still. Fail → do not chain; diagnose first.
    Human still approves keepers even when pass_candidate.
    """
    return json.dumps(
        _gate_i2v_clip(
            video_path,
            start_image_path=start_image_path or "",
            work_dir=work_dir or "",
        ),
        indent=2,
    )


@mcp.tool()
def extract_chain_lastframe(
    video_path: str,
    output_path: str = "",
    start_image_path: str = "",
) -> str:
    """
    Extract last frame for I2V chaining + usability vs f0/start.
    Only chain after human keep + usable_for_chain true.
    """
    return json.dumps(
        _extract_chain_lastframe(
            video_path,
            output_path=output_path or "",
            start_image_path=start_image_path or "",
        ),
        indent=2,
    )


@mcp.tool()
def recommend_polish(
    video_path: str = "",
    eyes_melted: bool = False,
    already_looks_good: bool = False,
    user_prefers_no_rife: bool = True,
) -> str:
    """
    Advise polish path. Saloon default: SeedVR-only @16fps (no RIFE).
    Always A/B vs the master — SeedVR can look worse (Saloon SS02 2026-08-20; keep original).
    mode=v2v generate_video is extend-only; latent clean is catalog v2v_upscale (mute RIFE).
    Skip polish if eyes melted or master already good.
    """
    return json.dumps(
        _recommend_polish(
            video_path or "",
            eyes_melted=eyes_melted,
            already_looks_good=already_looks_good,
            user_prefers_no_rife=user_prefers_no_rife,
        ),
        indent=2,
    )


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
        bundle: oral_insertion | missionary_sex | pov_insertion | doggy_sex | facial_cum | female_orgasm | lightning_i2v | smooth_character | … (merges with lora_ids). Local-only entries skip HF.
        force: Re-download even when present.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    results = _fetch_wan_video_loras(_cfg, lora_ids=ids, bundle=bundle, force=force)
    summary = _check_wan_video_loras_status(_cfg, ids)
    return json.dumps({"downloads": results, "status": summary}, indent=2)


@mcp.tool()
def check_nsfw_image_loras(lora_ids: str | list[str] = "") -> str:
    """
    Check curated NSFW still-image LoRAs (Illustrious / Pony intimacy lanes).

    Verifies local Stability Matrix Lora/ and remote ComfyUI when configured.
    Use bundle ids with resolve via list_nsfw_image_loras or download_nsfw_image_loras.

    Args:
        lora_ids: manga_nsfw_style, ntr_mix_style, pov_holding_pony, hentai_manga_pony. Empty = all.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    return json.dumps(_check_nsfw_image_loras_status(_cfg, ids, comfy_url=_comfy_url()), indent=2)


@mcp.tool()
def list_nsfw_image_loras(style: str = "") -> str:
    """
    List NSFW scene LoRAs for a style lane (ilustmix, pony, merged_dreams, anime).

    Pass style= to filter. Returns ids, weights, triggers, and bundle names for generate_image(loras=…).
    """
    if style:
        items = list_nsfw_image_loras_for_style(_catalog._find_style_key(style))
    else:
        items = []
        for lid, entry in NSFW_IMAGE_LORAS.items():
            row = {k: v for k, v in entry.items() if k != "id"}
            row["id"] = lid
            row["bundles"] = [b for b, ids in NSFW_IMAGE_LORA_BUNDLES.items() if lid in ids]
            items.append(row)
    return json.dumps({"style": style or None, "loras": items, "bundles": NSFW_IMAGE_LORA_BUNDLES}, indent=2)


@mcp.tool()
def download_nsfw_image_loras(
    lora_ids: str | list[str] = "",
    bundle: str = "",
    force: bool = False,
) -> str:
    """
    Download NSFW still-image LoRAs from Civitai into Stability Matrix Lora/.

    Bundles: illustrious_intimacy | illustrious_romance | pony_explicit | fantasy_romance.
    On remote ComfyUI setups, copy files to the GPU box Lora/ folder if download path is local-only.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    results = _fetch_nsfw_image_loras(_cfg, lora_ids=ids, bundle=bundle, force=force)
    summary = _check_nsfw_image_loras_status(_cfg, ids, comfy_url=_comfy_url())
    return json.dumps({"downloads": results, "status": summary}, indent=2)


@mcp.tool()
def resolve_nsfw_scene_loras(
    bundle: str = "",
    style: str = "",
    lora_ids: str | list[str] = "",
) -> str:
    """
    Build a loras=[{file, weight}, …] list for generate_image on explicit/intimacy beats.

    Example: resolve_nsfw_scene_loras(bundle=fantasy_romance, style=merged_dreams)
    → pass the loras field into generate_image unchanged.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    resolved = resolve_nsfw_lora_list(lora_ids=ids, bundle=bundle, style=style)
    return json.dumps({"loras": resolved}, indent=2)


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
def reload_catalog() -> str:
    """Re-read catalog.yaml from disk. Call after editing character_loras / styles without restarting MCP."""
    return json.dumps(_catalog.reload(), indent=2)


@mcp.tool()
def list_character_loras() -> str:
    """List trained character LoRAs (Frieren cast + Solo Leveling + Shooting Gallery) and install status."""
    _catalog.reload()
    models_dir = Path(_cfg["stability_matrix"]["models"])
    return json.dumps(
        _check_character_loras_on_disk(_catalog._data, models_dir),
        indent=2,
    )


@mcp.tool()
def resolve_character_loras(character: str, include_eye_lora: bool = True) -> str:
    """Build generate_image(loras=…) for a cast member.

    character: fern | frieren | darkness | ubel | flamme | cha_hae_in | jinah_sung |
    park_heejin | jessie | tatsumaki | eris | …
    Dedicated LoRA when catalog has one. Eris Greyrat and some others are baked into
    waijfu — returns identity_source=baked_in_checkpoint (prompt by name, optional Eyes LoRAs).
    Darkness also returns body_prompt_rule + mesh_source (GenerationHost turnaround plates).
    """
    _catalog.reload()
    resolved = _resolve_character_loras(
        _catalog._data, character, include_eye_lora=include_eye_lora
    )
    return json.dumps(resolved, indent=2)


@mcp.tool()
def lookup_character_identity(character: str, include_eye_lora: bool = True) -> str:
    """LoRA vs baked-into-checkpoint identity for a character name (Eris, Frieren, …).

    Prefer this when unsure whether a dedicated LoRA exists. Same payload as
    resolve_character_loras; identity_source is character_lora or baked_in_checkpoint.
    """
    _catalog.reload()
    return json.dumps(
        _lookup_character_identity(
            _catalog._data, character, include_eye_lora=include_eye_lora
        ),
        indent=2,
    )


@mcp.tool()
def list_baked_in_characters() -> str:
    """Characters known to be baked into a checkpoint (e.g. Eris Greyrat in waijfu_alpha).

    No LoRA file — prompt by name + tags on that style. Dedicated LoRAs still preferred
    for tight ID when available.
    """
    _catalog.reload()
    return json.dumps(
        {
            "ok": True,
            "baked_in": _list_baked_in_characters(_catalog._data),
            "usage": (
                "lookup_character_identity('eris') or resolve_character_loras('eris') → "
                "generate_image(style=waijfu, prompt includes Eris Greyrat + costume)."
            ),
        },
        indent=2,
    )


@mcp.tool()
def list_studio_docs() -> str:
    """List allowlisted .md/.txt lessons and storyboards CreateBrain can read.

    Includes LESSONS-WAN-I2V, NSFW stills, Das Booty beats, hardware map, etc.
    """
    return json.dumps(_list_studio_docs(), indent=2)


@mcp.tool()
def read_studio_doc(
    doc: str = "",
    path: str = "",
    max_chars: int = 24000,
    start_line: int = 1,
    max_lines: int = 0,
    query: str = "",
    context_lines: int = 8,
) -> str:
    """Read an allowlisted studio .md or .txt file.

    Args:
        doc: Short id from list_studio_docs (e.g. lessons-wan-i2v, path-bible, handoff).
        path: Or a path under <STUDIO_ROOT> / TheaterJobs.
        max_chars: Truncate long files (default 24000).
        start_line: 1-based start line (ignored when query is set).
        max_lines: If >0, only return that many lines.
        query: If set, return matching line windows (keyword chunk mode) instead of whole file.
        context_lines: Lines of context around each query hit.
    """
    return json.dumps(
        _read_studio_doc(
            doc=doc,
            path=path,
            max_chars=max_chars,
            start_line=start_line,
            max_lines=max_lines,
            query=query,
            context_lines=context_lines,
        ),
        indent=2,
    )


@mcp.tool()
def search_studio_docs(query: str, max_hits: int = 20) -> str:
    """Grep allowlisted studio docs for a phrase (Wan LoRA tips, gold standard, etc.)."""
    return json.dumps(_search_studio_docs(query, max_hits=max_hits), indent=2)


@mcp.tool()
def append_lesson(doc: str, bullet: str, heading: str = "") -> str:
    """Append one short factual bullet to an allowlisted LESSONS md (CreateBrain house knowledge).

    doc: lessons-wan-i2v | lessons-nsfw-stills | lessons-generation-host-cuda | …
    bullet: one lesson only (≤600 chars). No chat dumps.
    """
    return json.dumps(_append_lesson(doc, bullet, heading=heading), indent=2)


@mcp.tool()
def suggest_asset_name(
    project: str,
    scene: str,
    beat: str,
    view: str,
    stage: str,
    ext: str = "png",
    kind: str = "still",
) -> str:
    """Build delivery filename: {project}_{scene}_{beat}_{view}_{stage}.{ext}.

    See path-bible (ollama/coder/PATHS.md). Use before saving stills/clips for Coder handoff.
    """
    return json.dumps(
        _suggest_asset_name(
            project, scene, beat, view, stage, ext=ext, kind=kind
        ),
        indent=2,
    )


@mcp.tool()
def fetch_web_documentation(url: str, max_chars: int = 20000) -> str:
    """Fetch cleaned text from an allowlisted URL (HF, Civitai, GitHub, wiki, …).

    For character refs / model cards. Scrape ≠ install — use download_* tools after approval.
    """
    return json.dumps(
        _fetch_web_documentation(url, max_chars=max_chars), indent=2
    )


@mcp.tool()
def list_character_mesh_assets() -> str:
    """List GenerationHost character mesh / turnaround packs (catalog character_mesh_assets).

    Paths are under delivery assets/characters/<Name>/mesh_source — not TheaterJobs game/.
    See LESSONS-SET-FILL.md and resolve_character_loras(character=…) for body_prompt_rule.
    Darkness includes darkness_body_v1.glb/.blend + strip beat stems when mesh_v1_ready.
    """
    return json.dumps(
        {
            "assets": _list_character_mesh_assets(_catalog._data),
            "lessons": "<STUDIO_ROOT>/LESSONS-SET-FILL.md",
            "related_tools": [
                "list_set_mesh_assets",
                "list_solid_strip_maps",
                "resolve_character_loras",
            ],
            "usage": (
                "resolve_character_loras('darkness') for LoRAs + body_prompt_rule + mesh_source; "
                "list_set_mesh_assets() for casting_couch BG glb + locked plate; "
                "list_solid_strip_maps() for gray_cut/silhouette/depth/pose per beat; "
                "keep assets on GenerationHost; solid mesh > Body25 sticks for inpaint masks."
            ),
        },
        indent=2,
    )


@mcp.tool()
def list_set_mesh_assets() -> str:
    """List Blender set meshes (BG glb, locked plates, solid strip maps).

    Catalog key: set_mesh_assets (e.g. casting_couch). BG is exported Blender blockers — not AI room mesh.
    """
    return json.dumps(
        {
            "assets": _list_set_mesh_assets(_catalog._data),
            "lessons": "<STUDIO_ROOT>/LESSONS-SET-FILL.md",
            "related_tools": [
                "list_character_mesh_assets",
                "list_solid_strip_maps",
                "get_blender_workflow_playbook",
            ],
            "usage": (
                "list_solid_strip_maps(set_id='casting_couch') for per-beat maps; "
                "pose via kits/pose_solid_strip_beats.py; fill via mask_inpaint_prep + inpaint_advanced."
            ),
        },
        indent=2,
    )


@mcp.tool()
def list_solid_strip_maps(set_id: str = "casting_couch") -> str:
    """List solid-mesh strip maps (gray_cut / silhouette / depth / pose) for a Blender set.

    set_id: casting_couch (default). Returns on-disk paths + exists flags for each beat.
    """
    return json.dumps(
        _list_solid_strip_maps(_catalog._data, set_id=set_id),
        indent=2,
    )


@mcp.tool()
def resolve_style_lane(ask: str) -> str:
    """Parse a natural-language image ask into style_lanes (medium + mood + cast + recipe).

    Example ask: 'retro anime with cyber lighting of Esil in armor casting at a monster'
    Returns media, mood, cast axes, style checkpoint id, look_profile, prompt_tail,
    negative_extra, and loras. Then call resolve_character_loras for named cast and
    generate_image(style=..., loras=..., prompt with tails).
    """
    resolved = _resolve_style_lane(_catalog._data, ask)
    return json.dumps(resolved, indent=2)


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
def get_prompt_style(
    style: str = "",
    platform: str = "",
    food_group: str = "",
) -> str:
    """
    Compact prompt grammar for one catalog style or platform — call before writing prompts.

    Args:
        style: Catalog style id (ilustmix, pony, juggernaut, miracle_nsfw, …).
        platform: Studio platform id (illustrious, pony, flux, sdxl, wan_image, qwen_edit, action_combat).
        food_group: anime | fantasy | cyberpunk | photoreal (uses group default_style).
        Empty args: index of platforms and food groups.

    Returns prompt_style, prefix/negative hints, length caps, and generate_image style id.
    Prefer this over parsing full get_generation_context when writing Platform/Positive/Negative.
    """
    from studio.prompt_style import build_prompt_style_guide

    try:
        guide = build_prompt_style_guide(
            _catalog,
            style=style.strip(),
            platform=platform.strip(),
            food_group=food_group.strip(),
        )
    except ValueError as exc:
        return json.dumps({"error": str(exc), "hint": "get_prompt_style() with no args lists platforms"}, indent=2)
    return json.dumps(guide, indent=2)


@mcp.tool()
def compile_image_prompt(
    prompt: str,
    style: str = "",
    content_rating: str = "open",
) -> str:
    """
    Dedupe redundant action phrases and normalize NSFW euphemisms before ComfyUI.

    Use before generate_image when Jan wrote a verbose or clinical prompt.
    generate_image also auto-compiles; this tool previews changes without GPU.

    Args:
        prompt: Raw positive prompt from the agent or user.
        style: Optional catalog style (architecture hint only).
        content_rating: open (default) | sfw — sfw skips NSFW euphemism pass.
    """
    from studio.prompt_compile import compile_image_prompt as compile_prompt

    arch = ""
    if style.strip():
        try:
            arch = _catalog.resolve_architecture(_catalog._find_style_key(style.strip()))
        except (KeyError, ValueError):
            arch = ""
    compiled, report = compile_prompt(
        prompt,
        content_rating=content_rating.strip() or "open",
        architecture=arch,
    )
    return json.dumps({"compiled_prompt": compiled, **report}, indent=2)


@mcp.tool()
def get_action_combat_playbook(
    style: str = "anime",
    look: str = "",
) -> str:
    """
    Pose-first pipeline for fight / stab / gore stills — call before combat storyboard rows.

    Args:
        style: Catalog style for the keyframe (anime/WAI default, pony, juggernaut). Default anime.
        look: Alias for style (photoreal → juggernaut, wai → anime).

    Returns workflow steps, OpenPose editor URLs, prompt templates, firearm negatives,
    and generate_image_pose_guided defaults. Never use one-shot generate_image for these beats.
    """
    from studio.action_combat import build_action_combat_playbook

    return json.dumps(
        build_action_combat_playbook(style=style.strip(), look=look.strip()),
        indent=2,
    )


@mcp.tool()
def get_blender_workflow_playbook() -> str:
    """
    Blender MCP on GENERATION_HOST (5090) → pose/depth assets → generate_image_pose_guided.

    Call before combat/pose stills when using Blender instead of OpenPose web editors.
    Includes GPU exclusivity (Blender vs ComfyUI on the same RTX 5090).
    """
    from studio.blender_bridge import get_blender_workflow_playbook as _playbook

    return json.dumps(_playbook(), indent=2)


@mcp.tool()
def register_blender_control_maps(
    pose_path: str = "",
    depth_path: str = "",
    scene_id: str = "",
) -> str:
    """
    Validate Blender-exported control maps on disk before pose-guided generation.

    Args:
        pose_path: Local path to OpenPose-style skeleton PNG (Windows delivery or UNC).
        depth_path: Optional depth PNG from Blender.
        scene_id: Optional id for suggested Game-drive asset naming.
    """
    from studio.blender_bridge import register_blender_control_maps as _reg

    return json.dumps(
        _reg(_cfg, pose_path=pose_path, depth_path=depth_path, scene_id=scene_id),
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
        denoising_strength: 0.35–0.75 typical (honored with masks too; was previously forced to 1.0). Higher = more freedom inside the mask.
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
    end_image_path: str = "",
    video_path: str = "",
    concat_source: bool = True,
    num_frames: int = 0,
    frame_rate: float = 0,
    lora_ids: str | list[str] = "",
    lora_bundle: str = "",
    lora_weights: dict[str, float] | str | None = None,
    loras: list[dict[str, Any]] | str | None = None,
    use_painter_i2v: bool = False,
    motion_amplitude: float = 1.15,
    smooth_motion: bool = False,
    moe_preset: str = "",
    draft: bool = False,
) -> str:
    """
    Generate video via ComfyUI (remote generation-host when configured).

    Routing: user asks for 14B / NSFW motion → workflow_id=i2v (Wan 2.2 MoE HIGH+LOW; keep ComfyUI running).
    FLF2V (start+end keys): workflow_id=flf2v + image_path + end_image_path; prefer ~21f hard contact.
    Do NOT call generate_video_hero for 14B. Hero/Wan2GP is a separate tool. Do NOT use i2v_5b for uncensored NSFW.

    Keepers (MoE i2v/flf2v): omit moe_preset or moe_preset=quality (no Lightning). draft=True or moe_preset=fast = Lightning probe only.
    Action LoRAs: lora_bundle=oral_insertion|oral_deepthroat|missionary_sex|pov_insertion|doggy_sex|facial_cum (or lora_ids),
    or pass-through loras=[{file, weight, branch}] with branch high|low|both. Split weights via lora_weights or per-entry weight.

    REQUIRED preflight for NSFW action beats: plan_wan_beat / resolve_wan_action_loras(prompt=…) →
    check_wan_prompt → download if missing → pass lora_bundle=. Do not skip when a matching action pair exists
    (BJ soft without oral_insertion / deepthroat without oral_deepthroat are known failure modes). After gen: gate_i2v_clip before chain.

    Args:
        prompt: Scene description.
        mode: t2v, i2v, or v2v (video extend from last frame).
        style: Optional image style for prompt prefix/negative defaults.
        negative_prompt: Override negative prompt for Wan text encode nodes.
        workflow_id: Short catalog id: t2v, i2v_5b, i2v_5b_painter, v2v_5b, v2v_5b_painter, i2v, flf2v, i2v_wan21_native, i2v_gpu. Empty = auto. Do NOT pass the .json filename. For Wan 14B use i2v (MoE).
        content_rating: open (default) or sfw for optional safety negatives.
        image_path: Required for i2v/flf2v — exact local path from list_source_images (never invent D:\\Users\\...).
        end_image_path: Required for flf2v — last-frame key still.
        video_path: Required for v2v — local path to source clip to extend.
        concat_source: For v2v — append continuation to source clip (default true).
        num_frames: Optional frame count override (e.g. 65 for ~4s at 16fps; flf2v default 21).
        frame_rate: Optional output fps override (e.g. 16).
        lora_ids: Wan video LoRA id(s): comma-separated string or list (pov_insertion_i2v_high, …). MoE auto-pairs HIGH/LOW mates.
        lora_bundle: female_orgasm | lightning_i2v | oral_insertion | oral_deepthroat | ultimate_deepthroat | missionary_sex | pov_insertion | doggy_sex | facial_cum | smooth_character | … — merged with lora_ids.
        lora_weights: Optional {catalog_id: weight} for split HIGH/LOW (e.g. {"pov_insertion_i2v_high": 0.35, "pov_insertion_i2v_low": 1.0}).
        loras: Optional pass-through [{file, weight, branch}] and/or {id, weight, branch} — same shape as GenerationEngine.generate_video.
        use_painter_i2v: Inject PainterI2V on 5B path only (or workflow_id=i2v_5b_painter). Ignored on MoE i2v.
        motion_amplitude: PainterI2V strength 1.0–1.5 (default 1.15). MoE i2v gap: ignored on workflow_id=i2v — use prompt/amp discipline + action LoRAs instead.
        smooth_motion: Gentler 5B Painter path; on MoE i2v forces quality (no Lightning). Surprise: may also inject lora_bundle=smooth_character (face_naturalizer+camera_steady) — not a motion-smooth LoRA.
        moe_preset: quality|default (keepers, no Lightning) or fast (Lightning). Empty = engine default (quality unless draft/lightning bundle).
        draft: True = Lightning fast preset probe only. Keepers: leave False.
    """
    ids = _parse_lora_ids_arg(lora_ids)
    weights = _parse_lora_weights_arg(lora_weights)
    custom_loras = _parse_video_loras_arg(loras)
    resolved_loras = _resolve_generate_video_loras(
        lora_ids=ids,
        lora_bundle=lora_bundle or "",
        lora_weights=weights,
        loras=custom_loras,
    )
    # Soft preflight: NSFW action beat with no LoRAs → warn (still runs if agent insists).
    lora_preflight = _suggest_wan_action_lora(prompt or "", cfg=_cfg)
    has_loras = bool(resolved_loras) or bool(ids) or bool(lora_bundle) or bool(custom_loras)
    preflight_warning = None
    if (
        (mode or "").lower() == "i2v"
        and lora_preflight.get("recommended_bundle")
        and not has_loras
    ):
        preflight_warning = (
            f"Action LoRA checklist skipped: beat looks like "
            f"{lora_preflight['recommended_bundle']!r} (matched {lora_preflight.get('matched_on')!r}) "
            "but no lora_bundle/lora_ids/loras were passed. "
            "Call resolve_wan_action_loras then re-run with lora_bundle=… "
            "(prompt-only hard contact / bob / insertion often fails)."
        )
    try:
        nari_unload = _maybe_unload_nari_for_video(
            _cfg, workflow_id=workflow_id or "", mode=mode or ""
        )
        result = _engine.generate_video(
            prompt=prompt,
            mode=mode,
            style=style or None,
            negative_prompt=negative_prompt or None,
            workflow_id=workflow_id or None,
            content_rating=content_rating or "open",
            image_path=image_path or None,
            end_image_path=end_image_path or None,
            video_path=video_path or None,
            concat_source=concat_source,
            num_frames=num_frames or None,
            frame_rate=frame_rate or None,
            loras=resolved_loras,
            lora_ids=None if resolved_loras is not None else ids,
            lora_bundle="" if resolved_loras is not None else (lora_bundle or ""),
            use_painter_i2v=use_painter_i2v,
            motion_amplitude=motion_amplitude,
            smooth_motion=smooth_motion,
            moe_preset=moe_preset or None,
            draft=draft,
        )
        if isinstance(result, dict):
            result["nari_unload"] = nari_unload
            if preflight_warning:
                result["lora_preflight_warning"] = preflight_warning
                result["lora_preflight"] = {
                    "recommended_bundle": lora_preflight.get("recommended_bundle"),
                    "matched_on": lora_preflight.get("matched_on"),
                    "ready": lora_preflight.get("ready"),
                    "checklist": lora_preflight.get("checklist"),
                }
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="generate_video")
        err["ok"] = False
        if preflight_warning:
            err["lora_preflight_warning"] = preflight_warning
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
    Snapshot GPU backend policy: ComfyUI vs Wan2GP vs Forge, MCP lock, VRAM, allowed backends.

    Call before generate_video, generate_audio, or generate_video_hero — especially for
    offline agents (Jan, LM Studio) that cannot rely on Cursor-side enforcement alone.
    If forge.running is true, switch the generation host back to ComfyUI before MCP image/video.

    Routing: user asks for 14B → generate_video(workflow_id=i2v) on ComfyUI (keep it running).
    generate_video_hero is Wan2GP only — not the 14B path. Do not tell the user to stop
    Windows Stability Matrix when ComfyUI is on remote generation-host.
    """
    status = inspect_gpu_backend(_cfg, comfyui_running=_engine.comfy.is_running())
    status["nari_ollama"] = _nari_ollama_status(_cfg)
    return json.dumps(status, indent=2)


@mcp.tool()
def unload_nari_for_gpu(reason: str = "manual") -> str:
    """Unload nari / nari-prompt from GenerationHost Ollama so Wan/Forge/MOSS can use the 5090.

    Usually automatic before generate_video / generate_audio / generate_video_hero.
    Call manually if Ollama still holds VRAM after a long OI chat.
    """
    return json.dumps(_unload_nari_models(_cfg, reason=reason or "manual"), indent=2)


@mcp.tool()
def check_forge_backend() -> str:
    """
    Check whether Forge (A1111 API) is up on the generation host for ADetailer/hires stills.

    If running=true, ComfyUI is usually stopped. Use switch_stills_backend to flip.
    """
    return json.dumps(inspect_forge_backend(_cfg), indent=2)


@mcp.tool()
def switch_stills_backend(backend: str = "status", wait: bool = True) -> str:
    """
    Exclusive GPU switch on the generation host between ComfyUI and Forge (SSH + gpu_backend.sh).

    Args:
        backend: comfy | forge | status | stop-all
        wait: Wait until the target API is reachable (default true)

    Workflow for Jan: generate_image (Comfy) -> switch_stills_backend(forge) ->
    refine_image_forge -> switch_stills_backend(comfy) -> generate_video.
    """
    return json.dumps(_switch_stills_backend(_cfg, backend, wait=wait), indent=2)


@mcp.tool()
def generate_image_forge(
    prompt: str,
    negative_prompt: str = "",
    checkpoint: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    cfg: float = 6.0,
    seed: int = -1,
    adetailer: bool = True,
    ad_prompt: str = "",
) -> str:
    """
    txt2img on Forge (ADetailer on by default). Forge must be running.

    Prefer refine_image_forge after a Comfy still. Checkpoint examples:
    fantasyprime_25D.safetensors, homochiXLMaleFocused_20.safetensors.
    """
    try:
        result = _generate_image_forge(
            _cfg,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg,
            seed=seed,
            adetailer=adetailer,
            ad_prompt=ad_prompt,
        )
    except Exception as exc:
        return json.dumps({"ok": False, "error": humanize_error(exc)}, indent=2)
    return json.dumps(result, indent=2)


@mcp.tool()
def refine_image_forge(
    image_path: str,
    prompt: str,
    negative_prompt: str = "",
    checkpoint: str = "",
    denoising_strength: float = 0.35,
    steps: int = 28,
    cfg: float = 5.5,
    seed: int = -1,
    adetailer: bool = True,
    ad_prompt: str = "",
    ad_negative: str = "",
    ad_model: str = "face_yolov8n.pt",
    ad_denoising_strength: float = 0.4,
) -> str:
    """
    img2img refine on Forge with optional ADetailer. Forge must be running.

    Typical denoise 0.28–0.45 after a Comfy still. Then switch_stills_backend(comfy)
    before generate_video.

    For oral/insertion stills use eyes-only: ad_model=mediapipe_face_mesh_eyes_only
    and keep denoising_strength very low (≈0.05–0.10) so mouth/cock stay locked.
    """
    try:
        result = _refine_image_forge(
            _cfg,
            image_path=image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            denoising_strength=denoising_strength,
            steps=steps,
            cfg_scale=cfg,
            seed=seed,
            adetailer=adetailer,
            ad_prompt=ad_prompt,
            ad_negative=ad_negative,
            ad_model=ad_model,
            ad_denoising_strength=ad_denoising_strength,
        )
    except Exception as exc:
        return json.dumps({"ok": False, "error": humanize_error(exc)}, indent=2)
    return json.dumps(result, indent=2)


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
    Wan2GP Enhanced Lightning hero I2V — ONLY when the user explicitly says hero / Wan2GP / lip-sync.

    NOT the 14B path. User said 14B → use generate_video(mode=i2v, workflow_id=i2v) on ComfyUI instead.
    If ComfyUI is up you will get gpu_backend_conflict; do not tell them to stop Windows Stability Matrix
    for remote generation-host — keep ComfyUI and switch to generate_video.

    Requires: ComfyUI stopped (remote: ssh GENERATION_HOST '~/bin/gpu_backend.sh stop'), Wan2GP Gradio UI stopped,
    Lightning v2 weights installed. Auto-starts Wan2GP MCP on gpu_backend.wan2gp_mcp_port when configured.

    Args:
        prompt: Motion/scene description (e.g. Japanese bow, subtle forward lean).
        image_path: Exact local path from list_source_images.
        negative_prompt: Optional negatives.
        video_length: Frame count (default 49 ≈ 3s at 16fps).
        resolution: e.g. 832x480.
        seed: -1 = random.
        motion_amplitude: Wan2GP motion strength (default 1.05 for subtle bow).
    """
    try:
        nari_unload = _maybe_unload_nari_for_hero(_cfg)
        result = _engine.generate_video_hero(
            prompt=prompt,
            image_path=image_path,
            negative_prompt=negative_prompt,
            video_length=video_length,
            resolution=resolution,
            seed=seed,
            motion_amplitude=motion_amplitude,
        )
        if isinstance(result, dict):
            result["nari_unload"] = nari_unload
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
    """Return canonical local folders for MCP, ComfyUI, Wan2GP outputs + source_image_dirs notes."""
    return json.dumps(media_paths(_cfg), indent=2)


@mcp.tool()
def list_source_images(query: str = "", max_files: int = 40) -> str:
    """
    Find local stills for I2V / edits. Call this instead of guessing image_path.

    Scans Desktop\\New Images and delivery\\User Import (and related). Pass files[].path exactly.
    """
    return json.dumps(
        _list_source_images(_cfg, query=query, max_files=max_files),
        indent=2,
    )


@mcp.tool()
def delivery_media_root() -> str:
    """Show D:\\GenerationHost Images and Videos root + top-level folders."""
    return json.dumps(_media_root_info(_cfg), indent=2)


@mcp.tool()
def list_delivery_media(
    subdir: str = "",
    query: str = "",
    kind: str = "all",
    max_files: int = 60,
    recursive: bool = True,
) -> str:
    """
    List images/videos under the GenerationHost delivery folder.

    Args:
        subdir: e.g. User Import, Images, Video, clips. Empty = whole delivery root.
        query: Filename substring filter.
        kind: all | image | video
    """
    return json.dumps(
        _list_delivery_media(
            _cfg,
            subdir=subdir,
            query=query,
            kind=kind,
            max_files=max_files,
            recursive=recursive,
        ),
        indent=2,
    )


@mcp.tool()
def view_delivery_image(path: str, max_edge: int = 1280) -> list:
    """
    Load an image so you can SEE it (preview bytes + path). Use after generate_* to review.

    Args:
        path: Absolute path, or path relative to delivery root.
        max_edge: Max preview size for vision context.
    """
    meta, preview = _view_delivery_image_payload(_cfg, path, max_edge=max_edge)
    if preview is None:
        return [json.dumps(meta, indent=2)]
    return [json.dumps(meta, indent=2), Image(data=preview, format="jpeg")]


@mcp.tool()
def view_delivery_video_frame(
    path: str,
    time_seconds: float = 0.5,
    max_edge: int = 1280,
) -> list:
    """Extract one video frame so you can SEE the clip (ffmpeg preview + path)."""
    meta, preview = _view_delivery_video_frame_payload(
        _cfg, path, time_seconds=time_seconds, max_edge=max_edge
    )
    if preview is None:
        return [json.dumps(meta, indent=2)]
    return [json.dumps(meta, indent=2), Image(data=preview, format="jpeg")]


@mcp.tool()
def copy_delivery_media(src: str, dest_relative: str, overwrite: bool = False) -> str:
    """Copy a file inside the GenerationHost delivery folder sandbox."""
    return json.dumps(
        _copy_delivery_media(_cfg, src, dest_relative, overwrite=overwrite),
        indent=2,
    )


@mcp.tool()
def move_delivery_media(src: str, dest_relative: str, overwrite: bool = False) -> str:
    """Move a file inside the GenerationHost delivery folder sandbox."""
    return json.dumps(
        _move_delivery_media(_cfg, src, dest_relative, overwrite=overwrite),
        indent=2,
    )


@mcp.tool()
def rename_delivery_media(src: str, new_name: str, overwrite: bool = False) -> str:
    """Rename a delivery file in place (filename only)."""
    return json.dumps(
        _rename_delivery_media(_cfg, src, new_name, overwrite=overwrite),
        indent=2,
    )


@mcp.tool()
def open_delivery_in_explorer(path: str = "") -> str:
    """Reveal a delivery file/folder in Windows Explorer."""
    return json.dumps(_open_delivery_in_explorer(_cfg, path), indent=2)


@mcp.tool()
def recycle_delivery_media(path: str) -> str:
    """
    Send a delivery (or Desktop\\New Images) file/folder to the Recycle Bin.

    Never hard-deletes. Refuses paths outside the delivery sandbox.
    Use when discarding failed gens / junk reviews — not for permanent wipe.
    """
    return json.dumps(_recycle_delivery_media(_cfg, path), indent=2)


@mcp.tool()
def comfy_queue_status() -> str:
    """
    ComfyUI queue + light system stats on the generation host.

    Use before starting create/Wan work or when checking if the box is busy.
    """
    import urllib.error
    import urllib.request

    url = _comfy_url().rstrip("/")
    out: dict[str, Any] = {"comfy_url": url}

    def _get(path: str) -> Any:
        req = urllib.request.Request(f"{url}{path}")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        queue = _get("/queue")
        running = queue.get("queue_running") or []
        pending = queue.get("queue_pending") or []
        out["queue_running"] = len(running) if isinstance(running, list) else "?"
        out["queue_pending"] = len(pending) if isinstance(pending, list) else "?"
        out["busy"] = bool(running) or bool(pending)
        out["queue"] = queue
    except Exception as exc:  # noqa: BLE001
        out["ok"] = False
        out["error"] = f"queue: {exc}"
        return json.dumps(out, indent=2)
    try:
        out["system_stats"] = _get("/system_stats")
    except Exception as exc:  # noqa: BLE001
        out["system_stats_error"] = str(exc)
    out["ok"] = True
    return json.dumps(out, indent=2)


@mcp.tool()
def interpolate_video(
    video_path: str,
    target_fps: float = 24.0,
    method: str = "rife",
    crf: int = 18,
) -> str:
    """
    Upsample clip frame rate on the main rig (not generation-host).

    Args:
        video_path: Source MP4/WebM path.
        target_fps: Output fps (default 24).
        method: rife (RIFE-ncnn-vulkan quality path, default) or minterpolate (ffmpeg MCI CPU).
        crf: libx264 quality (lower = larger/better; default 18).
    """
    try:
        result = _interpolate_video(
            _cfg,
            video_path,
            target_fps=target_fps,
            method=method,
            output_dir=Path(video_path).expanduser().resolve().parent,
            crf=crf,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="interpolate_video")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def check_local_post() -> str:
    """
    Check main-rig Wan polish stack: .venv-post + AnimeSharp, RIFE-ncnn, SeedVR2 3B FP8.
    Generation stays on generation-host; use before polish_wan_best / polish_wan_video.
    """
    return json.dumps(_check_local_post(_cfg), indent=2)


@mcp.tool()
def upscale_video_local(
    video_path: str,
    model: str = "anime_sharp_2x",
    crf: int = 17,
) -> str:
    """
    CUDA upscale a Wan MP4 on the main rig (RTX 5060 Ti via .venv-post + spandrel).

    Args:
        video_path: Source clip (usually after interpolate, or raw 16fps master).
        model: anime_sharp_2x (default, clean anime) or realesrgan_anime_4x.
        crf: libx264 quality for re-encode (default 17).
    """
    try:
        result = _upscale_video_local(
            _cfg,
            video_path,
            model=model,
            output_dir=Path(video_path).expanduser().resolve().parent,
            crf=crf,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="upscale_video_local")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def polish_wan_video(
    video_path: str,
    target_fps: float = 24.0,
    upscale_model: str = "anime_sharp_2x",
    skip_interpolate: bool = False,
    skip_upscale: bool = False,
    crf: int = 17,
    interpolate_method: str = "minterpolate",
) -> str:
    """
    Legacy/fast main-rig polish: interpolate then AnimeSharp CUDA upscale.
    For best free quality use polish_wan_best (RIFE → SeedVR2) instead.

    Args:
        video_path: Final spliced Wan MP4.
        target_fps: Interpolation target (default 24).
        upscale_model: anime_sharp_2x or realesrgan_anime_4x.
        skip_interpolate / skip_upscale: run only one stage if needed.
        crf: encode quality.
        interpolate_method: minterpolate (default legacy) or rife.
    """
    try:
        result = _polish_wan_video(
            _cfg,
            video_path,
            target_fps=target_fps,
            upscale_model=upscale_model,
            skip_interpolate=skip_interpolate,
            skip_upscale=skip_upscale,
            crf=crf,
            interpolate_method=interpolate_method,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="polish_wan_video")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def polish_wan_best(
    video_path: str,
    target_fps: float = 24.0,
    skip_interpolate: bool = False,
    skip_upscale: bool = False,
    crf: int = 17,
    seedvr2_resolution: int = 1080,
    seedvr2_batch_size: int = 5,
    seedvr2_blocks_to_swap: int = 16,
) -> str:
    """
    Best free main-rig polish for Wan: RIFE-ncnn → SeedVR2 3B FP8 (16GB-safe).
    Use on a locked master cut only. One GPU job at a time.

    Args:
        video_path: Locked master MP4 (e.g. Saloon keeper).
        target_fps: RIFE target fps (default 24).
        skip_interpolate / skip_upscale: run one stage only.
        crf: encode quality for RIFE re-encode.
        seedvr2_resolution: short-side target (1080 default; try 1440 if VRAM allows).
        seedvr2_batch_size: must be 4n+1 (5, 9, 13…).
        seedvr2_blocks_to_swap: BlockSwap for 16GB (16 default; raise on OOM).
    """
    try:
        result = _polish_wan_best(
            _cfg,
            video_path,
            target_fps=target_fps,
            skip_interpolate=skip_interpolate,
            skip_upscale=skip_upscale,
            crf=crf,
            seedvr2_resolution=seedvr2_resolution,
            seedvr2_batch_size=seedvr2_batch_size,
            seedvr2_blocks_to_swap=seedvr2_blocks_to_swap,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="polish_wan_best")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def concat_video_clips(paths_json: str, output_path: str = "") -> str:
    """
    Lossless-concat MP4s (same codec/fps). paths_json = JSON list of absolute paths.

    Args:
        paths_json: e.g. '["D:/.../a.mp4","D:/.../b.mp4"]'
        output_path: optional dest; default first_stem_concat.mp4 beside first clip.
    """
    try:
        paths = json.loads(paths_json)
        if not isinstance(paths, list):
            raise ValueError("paths_json must be a JSON list of strings")
        return json.dumps(
            _concat_video_clips(_cfg, [str(p) for p in paths], output_path=output_path),
            indent=2,
        )
    except Exception as exc:
        err = humanize_error(exc, context="concat_video_clips")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def splice_pingpong(
    video_path: str,
    then_forward: bool = True,
    output_path: str = "",
) -> str:
    """
    D-style lengthen: forward + reverse (+ optional forward again). Good for bobbing loops.

    Args:
        video_path: Source segment (often first half of a clip).
        then_forward: if true, append forward once more (~D_pingpong_then_half).
        output_path: optional dest path.
    """
    try:
        return json.dumps(
            _splice_pingpong(
                _cfg,
                video_path,
                output_path=output_path,
                then_forward=then_forward,
            ),
            indent=2,
        )
    except Exception as exc:
        err = humanize_error(exc, context="splice_pingpong")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def splice_crossfade_loop(
    video_path: str,
    fade_sec: float = 0.25,
    output_path: str = "",
) -> str:
    """E-style soft loop: two copies joined with ffmpeg xfade."""
    try:
        return json.dumps(
            _splice_crossfade_loop(
                _cfg,
                video_path,
                fade_sec=fade_sec,
                output_path=output_path,
            ),
            indent=2,
        )
    except Exception as exc:
        err = humanize_error(exc, context="splice_crossfade_loop")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def splice_pose_matched_loop(
    video_path: str,
    target_sec: float = 19.0,
    rewind_max: int = 12,
    output_path: str = "",
) -> str:
    """
    Pose-matched D-style loop: search ±rewind_max frames for best join (quieter drool/pose pops).

    Args:
        video_path: Source master (e.g. 12s chain before climax).
        target_sec: Desired bobbing length before climax.
        rewind_max: Max frames to search back from nominal half (default 12).
        output_path: optional dest.
    """
    try:
        return json.dumps(
            _splice_pose_matched_loop(
                _cfg,
                video_path,
                target_sec=target_sec,
                rewind_max=rewind_max,
                output_path=output_path,
            ),
            indent=2,
        )
    except Exception as exc:
        err = humanize_error(exc, context="splice_pose_matched_loop")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def rewrite_chapter_phonetic(
    text: str,
    chapter: int = 0,
    stem: str = "",
    also_speak: bool = False,
) -> str:
    """DeskHost-owned: rewrite chapter prose for clear Kokoro readback.

    Pass the chapter body in `text` (EdgeVoice resolves files on the Pi and forwards text).
    Saves a phonetic .txt via DeskHost tools; set also_speak=true to also synthesize a WAV
    with generate_speech_kokoro / Kokoro :8090 when available.
    """
    result = _rewrite_chapter_phonetic(
        _cfg,
        text=text,
        chapter=chapter or None,
        stem=stem,
        also_speak=also_speak,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def check_kokoro_backend() -> str:
    """Kokoro narrate TTS on generation host :8090 — CPU service; no GPU lock. Owned by DeskHost."""
    return json.dumps(inspect_kokoro_backend(_cfg), indent=2)


@mcp.tool()
def list_kokoro_voices() -> str:
    """List voices from Kokoro GET /v1/voices."""
    try:
        return json.dumps(_list_kokoro_voices(_cfg), indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="list_kokoro_voices")
        err["ok"] = False
        return json.dumps(err, indent=2)


@mcp.tool()
def generate_speech_kokoro(
    text: str,
    voice: str = "",
    speed: float = 0.0,
    filename: str = "",
) -> str:
    """
    Synthesize speech via Kokoro narrate HTTP API (WAV). Does not take the GPU lock.

    Args:
        text: Words to speak.
        voice: Voice id (empty = config default, often am_michael).
        speed: 0 = use config default; typical 0.8–1.0.
        filename: Optional output stem (saved under MCP outputs/ + delivery audio/).
    """
    try:
        result = synthesize_kokoro(
            _cfg,
            text,
            voice=voice,
            speed=None if speed <= 0 else speed,
            output_dir=Path(_cfg.get("_root", ROOT)) / "outputs",
            filename=filename,
        )
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="generate_speech_kokoro")
        err["ok"] = False
        return json.dumps(err, indent=2)


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
        nari_unload = _maybe_unload_nari_for_audio(_cfg)
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
        if isinstance(result, dict):
            result["nari_unload"] = nari_unload
        return json.dumps(result, indent=2)
    except Exception as exc:
        err = humanize_error(exc, context="generate_audio")
        err["ok"] = False
        return json.dumps(err, indent=2)


MCP_TOOL_COUNT = len(mcp._tool_manager._tools)

if __name__ == "__main__":
    mcp.run()

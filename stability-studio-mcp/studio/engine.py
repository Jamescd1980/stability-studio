from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from studio.catalog import StyleCatalog
from studio.comfy_client import ComfyUIClient
from studio.content_safety import apply_content_policy, resolve_style_for_rating
from studio.invoke_client import InvokeAIClient
from studio.hardware_profile import (
    ANATOMY_NEGATIVE_HINT,
    ANATOMY_POSITIVE_HINT,
    apply_video_safety_caps,
    build_hardware_profile,
    clamp_image_params,
    clamp_video_params,
    fit_i2v_dimensions,
)
from studio.error_messages import humanize_error
from studio.video_utils import concat_videos, extract_last_frame
from studio.checkpoint_metadata import validate_style_architecture
from studio.face_detail_assets import ensure_face_detail_ready
from studio.edit_pipeline import (
    ART_FOOD_GROUPS,
    enrich_edit_prompts,
    plan_edit,
    resolve_style_for_edit,
    verify_edit_result,
)
from studio.image_editing_assets import (
    controlnet_files_for_architecture,
    ensure_extended_reference,
    is_ipadapter_supported,
)
from studio.ip_adapter_assets import (
    default_flag_reference_path,
    image_dimensions,
    write_region_mask_png,
)
from studio.segmentation import segment_image_to_mask
from studio.moss_workflow_builder import (
    build_moss_sound_effect_workflow,
    build_moss_speech_workflow,
    build_moss_voice_design_workflow,
)
from studio.audio_post import estimate_voice_max_tokens, polish_voice_instruction, trim_leading_trailing_silence
from studio.output_paths import deliver_files
from studio.wan_video_loras import apply_smooth_motion_preset, resolve_lora_list
from studio.workflow_builder import (
    append_face_detailer_workflow,
    build_advanced_inpaint_workflow,
    build_controlnet_ipadapter_txt2img_workflow,
    build_controlnet_txt2img_workflow,
    build_flux2_klein_txt2img_workflow,
    build_i2i_workflow,
    build_inpaint_workflow,
    build_ipadapter_txt2img_workflow,
    build_txt2img_workflow,
    build_wan21_i2v_ui_workflow,
    inject_i2v_enhancements_ui_workflow,
    inject_i2v_native_quality,
    inject_i2v_ui_workflow,
    inject_prompts_ui_workflow,
    is_flux_checkpoint,
)
from studio.workflow_converter import ui_to_api


class GenerationEngine:
    def __init__(self, cfg: dict[str, Any], catalog: StyleCatalog) -> None:
        self.cfg = cfg
        self.catalog = catalog
        comfy_url = cfg.get("comfyui", {}).get("url", "http://127.0.0.1:8188")
        invoke_url = cfg.get("invokeai", {}).get("url", "http://127.0.0.1:9090")
        timeout = int(cfg.get("comfyui", {}).get("timeout_seconds", 600))
        self.comfy = ComfyUIClient(comfy_url, timeout=timeout)
        self.invoke = InvokeAIClient(invoke_url, timeout=timeout)
        self.output_dir = Path(cfg.get("_root", ".")) / "outputs"
        self._workflow_ui_cache: dict[tuple[str, float], dict[str, Any]] = {}

    def _resolve_generation_context(
        self,
        *,
        style: str | None,
        prompt: str,
        negative_prompt: str | None = None,
        checkpoint: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        rating = content_rating or self.cfg.get("default_content_rating", "open")
        style_cfg = self.catalog.resolve_style(style)
        resolved_style = (
            self.catalog._find_style_key(style)
            if style
            else self.cfg.get("default_style", "juggernaut")
        )
        ckpt = checkpoint or style_cfg.get("checkpoint")
        if not ckpt:
            raise ValueError("No checkpoint configured for this style")
        resolved_style, ckpt = resolve_style_for_rating(resolved_style, ckpt, rating)
        prefix = style_cfg.get("prompt_prefix", "")
        base_neg = negative_prompt or style_cfg.get("negative_prompt", "")
        full_prompt, neg = apply_content_policy(
            prompt=prompt,
            positive_prefix=prefix,
            negative_prompt=base_neg,
            content_rating=rating,
        )
        defaults = self.catalog.resolve_generation_defaults(resolved_style)
        merged_loras = loras if loras is not None else style_cfg.get("loras", [])
        return {
            "rating": rating,
            "style_cfg": style_cfg,
            "resolved_style": resolved_style,
            "ckpt": ckpt,
            "full_prompt": full_prompt,
            "neg": neg,
            "defaults": defaults,
            "merged_loras": merged_loras,
        }

    def _save_comfy_outputs(
        self,
        outputs: list[dict[str, Any]],
        *,
        extensions: tuple[str, ...],
    ) -> list[str]:
        saved: list[str] = []
        for file_info in outputs:
            if file_info.get("filename", "").lower().endswith(extensions):
                saved.append(str(self.comfy.download_file(file_info, self.output_dir)))
        return saved

    def _queue_workflow_and_save(
        self,
        workflow: dict[str, Any],
        *,
        extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp"),
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        prompt_id = self.comfy.queue_prompt(workflow)
        history = self.comfy.wait_for_completion(prompt_id)
        outputs = self.comfy.collect_outputs(history)
        return prompt_id, outputs, self._save_comfy_outputs(outputs, extensions=extensions)

    def hardware_context(self) -> dict[str, Any]:
        return build_hardware_profile(self.cfg, self.comfy)

    def backend_status(self) -> dict[str, bool]:
        return {
            "comfyui": self.comfy.is_running(),
            "invokeai": self.invoke.is_running(),
        }

    def pick_backend(self, preferred: str | None = None) -> str:
        preferred = preferred or self.cfg.get("default_backend", "auto")
        status = self.backend_status()
        if preferred == "comfyui":
            if not status["comfyui"]:
                raise RuntimeError("ComfyUI is not running. Launch it from Stability Matrix.")
            return "comfyui"
        if preferred == "invoke":
            if not status["invokeai"]:
                raise RuntimeError("InvokeAI is not running. Launch it from Stability Matrix.")
            return "invoke"
        if status["comfyui"]:
            return "comfyui"
        if status["invokeai"]:
            return "invoke"
        raise RuntimeError("Neither ComfyUI nor InvokeAI is running. Start one from Stability Matrix.")

    def _apply_face_detail_if_requested(
        self,
        workflow: dict[str, Any],
        *,
        use_face_detail: bool,
        flux2: bool,
        defaults: dict[str, Any],
        cfg_scale: float,
        sampler_name: str,
        scheduler_name: str,
    ) -> dict[str, Any] | None:
        if not use_face_detail:
            return None
        if flux2:
            return {"applied": False, "reason": "Flux2 checkpoints do not support FaceDetailer yet"}
        comfy_url = self.cfg.get("comfyui", {}).get("url", "http://127.0.0.1:8188")
        ensure_face_detail_ready(self.cfg, comfy_url)
        pass_cfg = defaults.get("face_detail_pass") or {}
        if not isinstance(pass_cfg, dict):
            pass_cfg = {}
        run_seed = int(workflow.get("3", {}).get("inputs", {}).get("seed", 0))
        append_face_detailer_workflow(
            workflow,
            seed=run_seed,
            detail_steps=int(pass_cfg.get("steps", 20)),
            detail_cfg=float(pass_cfg.get("cfg", cfg_scale)),
            detail_denoise=float(pass_cfg.get("denoise", 0.45)),
            sampler=str(pass_cfg.get("sampler", sampler_name)),
            scheduler=str(pass_cfg.get("scheduler", scheduler_name)),
            guide_size=float(pass_cfg.get("guide_size", 384.0)),
            max_size=float(pass_cfg.get("max_size", 1024.0)),
        )
        return {
            "applied": True,
            "detector": "bbox/face_yolov8m.pt",
            "sam": "sam_vit_b_01ec64.pth",
            "detail_steps": int(pass_cfg.get("steps", 20)),
            "detail_denoise": float(pass_cfg.get("denoise", 0.45)),
        }

    def generate_image(
        self,
        *,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        checkpoint: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        seed: int | None = None,
        sampler: str | None = None,
        scheduler: str | None = None,
        face_detail: bool | None = None,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        ctx = self._resolve_generation_context(
            style=style,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            loras=loras,
            content_rating=content_rating,
        )
        rating = ctx["rating"]
        style_cfg = ctx["style_cfg"]
        resolved_style = ctx["resolved_style"]
        ckpt = ctx["ckpt"]
        full_prompt = ctx["full_prompt"]
        neg = ctx["neg"]
        defaults = ctx["defaults"]
        merged_loras = ctx["merged_loras"]

        w = width or defaults.get("width", 1024)
        h = height or defaults.get("height", 1024)
        st = steps or defaults.get("steps", 28)
        limits = self.hardware_context().get("generation_limits", {})
        w, h, st, clamped = clamp_image_params(w, h, st, limits)
        cfg_scale = cfg if cfg is not None else defaults.get("cfg", 7.0)
        sampler_name = sampler or defaults.get("sampler", "dpmpp_2m")
        scheduler_name = scheduler or defaults.get("scheduler", "karras")
        use_face_detail = (
            face_detail if face_detail is not None else bool(defaults.get("face_detail", False))
        )

        chosen = self.pick_backend(backend)

        if chosen == "invoke":
            model_key = ckpt.replace(".safetensors", "")
            lora_key = None
            lora_weight = 0.75
            if merged_loras:
                lora_key = merged_loras[0].get("name") or merged_loras[0].get("file")
                lora_weight = float(merged_loras[0].get("weight", 0.75))
            result = self.invoke.generate_image_simple(
                prompt=full_prompt,
                negative_prompt=neg,
                width=w,
                height=h,
                steps=st,
                cfg_scale=cfg_scale,
                seed=seed,
                model_key=model_key,
                lora_key=lora_key,
                lora_weight=lora_weight,
            )
            return {
                "backend": "invokeai",
                "style": resolved_style,
                "checkpoint": ckpt,
                "prompt": full_prompt,
                "negative_prompt": neg,
                "result": result,
            }

        flux2 = style_cfg.get("architecture") in {"flux2", "flux2_klein"} or is_flux_checkpoint(ckpt)
        if flux2:
            flux2_cfg = style_cfg.get("flux2", {})
            workflow = build_flux2_klein_txt2img_workflow(
                unet=ckpt,
                clip=flux2_cfg.get("clip", "qwen_3_8b_fp8mixed.safetensors"),
                vae=flux2_cfg.get("vae", "flux2-vae.safetensors"),
                positive=full_prompt,
                negative=neg,
                width=w,
                height=h,
                seed=seed,
                steps=st,
                cfg=cfg_scale,
                sampler=sampler_name if sampler_name in {"euler", "euler_cfg_pp", "heun", "dpmpp_2m"} else "euler",
            )
        else:
            workflow = build_txt2img_workflow(
                checkpoint=ckpt,
                positive=full_prompt,
                negative=neg,
                width=w,
                height=h,
                seed=seed,
                steps=st,
                cfg=cfg_scale,
                sampler=sampler_name,
                scheduler=scheduler_name,
                loras=merged_loras,
            )

        face_detail_info = self._apply_face_detail_if_requested(
            workflow,
            use_face_detail=use_face_detail,
            flux2=flux2,
            defaults=defaults,
            cfg_scale=cfg_scale,
            sampler_name=sampler_name,
            scheduler_name=scheduler_name,
        )

        prompt_id, outputs, saved = self._queue_workflow_and_save(workflow)

        result = {
            "backend": "comfyui",
            "style": resolved_style,
            "checkpoint": ckpt,
            "content_rating": rating,
            "prompt": full_prompt,
            "negative_prompt": neg,
            "width": w,
            "height": h,
            "steps": st,
            "cfg": cfg_scale,
            "sampler": sampler_name,
            "scheduler": scheduler_name,
            "loras": merged_loras or None,
            "face_detail": face_detail_info,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if clamped:
            result["clamped_to_limits"] = clamped
        return result

    def generate_image_guided(
        self,
        *,
        guide_image_path: str,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        checkpoint: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        seed: int | None = None,
        ipadapter_weight: float = 0.72,
        ipadapter_weight_type: str = "style and composition",
        ipadapter_ref_size: int = 512,
        face_detail: bool | None = None,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        """Txt2img from scratch with IP-Adapter composition lock from a guide image."""
        ctx = self._resolve_generation_context(
            style=style,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            loras=loras,
            content_rating=content_rating,
        )
        rating = ctx["rating"]
        style_cfg = ctx["style_cfg"]
        resolved_style = ctx["resolved_style"]
        ckpt = ctx["ckpt"]
        full_prompt = ctx["full_prompt"]
        neg = ctx["neg"]
        defaults = ctx["defaults"]
        merged_loras = ctx["merged_loras"]

        guide = Path(guide_image_path)
        if not guide.is_file():
            raise FileNotFoundError(f"Guide image not found: {guide}")

        if width and height:
            w, h = width, height
        else:
            w, h = image_dimensions(guide)

        st = steps or defaults.get("steps", 30)
        limits = self.hardware_context().get("generation_limits", {})
        w, h, st, clamped = clamp_image_params(w, h, st, limits)
        cfg_scale = cfg if cfg is not None else defaults.get("cfg", 5.0)
        sampler = defaults.get("sampler", "dpmpp_2m")
        scheduler = defaults.get("scheduler", "karras")

        uploaded = self.comfy.upload_image(guide)
        chosen = self.pick_backend(backend)
        if chosen == "invoke":
            raise NotImplementedError("IP-Adapter guided generation requires ComfyUI.")

        arch = style_cfg.get("architecture") or self.catalog.resolve_architecture(resolved_style)
        flux2 = arch in {"flux2", "flux2_klein"} or is_flux_checkpoint(ckpt)
        use_face_detail = (
            face_detail if face_detail is not None else bool(defaults.get("face_detail", False))
        )

        workflow = build_ipadapter_txt2img_workflow(
            checkpoint=ckpt,
            positive=full_prompt,
            negative=neg,
            guide_image_filename=uploaded,
            width=w,
            height=h,
            seed=seed,
            steps=st,
            cfg=cfg_scale,
            sampler=sampler,
            scheduler=scheduler,
            loras=merged_loras,
            ipadapter_weight=float(ipadapter_weight),
            ipadapter_weight_type=ipadapter_weight_type,
            ipadapter_ref_size=int(ipadapter_ref_size),
        )

        face_detail_info = self._apply_face_detail_if_requested(
            workflow,
            use_face_detail=use_face_detail,
            flux2=flux2,
            defaults=defaults,
            cfg_scale=cfg_scale,
            sampler_name=sampler,
            scheduler_name=scheduler,
        )

        prompt_id, outputs, saved = self._queue_workflow_and_save(workflow)

        result = {
            "backend": "comfyui",
            "mode": "guided_txt2img",
            "guide_image": str(guide),
            "ipadapter_weight": ipadapter_weight,
            "face_detail": face_detail_info,
            "prompt": full_prompt,
            "negative_prompt": neg,
            "width": w,
            "height": h,
            "steps": st,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if clamped:
            result["clamped_to_limits"] = clamped
        return result

    def generate_image_controlnet(
        self,
        *,
        guide_image_path: str,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        checkpoint: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        seed: int | None = None,
        depth_strength: float = 0.52,
        canny_strength: float = 0.62,
        canny_low_threshold: float = 0.25,
        canny_high_threshold: float = 0.6,
        reference_image_path: str | None = None,
        ipadapter_weight: float = 0.72,
        ipadapter_weight_type: str = "style and composition",
        ipadapter_ref_size: int = 512,
        face_detail: bool | None = None,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        """Txt2img with depth + canny ControlNet maps from a guide image."""
        ctx = self._resolve_generation_context(
            style=style,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            loras=loras,
            content_rating=content_rating,
        )
        rating = ctx["rating"]
        style_cfg = ctx["style_cfg"]
        resolved_style = ctx["resolved_style"]
        ckpt = ctx["ckpt"]
        full_prompt = ctx["full_prompt"]
        neg = ctx["neg"]
        defaults = ctx["defaults"]
        merged_loras = ctx["merged_loras"]

        guide = Path(guide_image_path)
        if not guide.is_file():
            raise FileNotFoundError(f"Guide image not found: {guide}")

        if width and height:
            w, h = width, height
        else:
            w, h = image_dimensions(guide)

        st = steps or defaults.get("steps", 30)
        limits = self.hardware_context().get("generation_limits", {})
        w, h, st, clamped = clamp_image_params(w, h, st, limits)
        cfg_scale = cfg if cfg is not None else defaults.get("cfg", 5.0)
        sampler = defaults.get("sampler", "dpmpp_2m")
        scheduler = defaults.get("scheduler", "karras")

        uploaded = self.comfy.upload_image(guide)
        chosen = self.pick_backend(backend)
        if chosen == "invoke":
            raise NotImplementedError("ControlNet guided generation requires ComfyUI.")

        arch = style_cfg.get("architecture") or self.catalog.resolve_architecture(resolved_style)
        cn_files = controlnet_files_for_architecture(arch)
        arch_check = validate_style_architecture(self.cfg, resolved_style, arch, ckpt)
        flux2 = arch in {"flux2", "flux2_klein"} or is_flux_checkpoint(ckpt)
        use_face_detail = (
            face_detail if face_detail is not None else bool(defaults.get("face_detail", False))
        )

        ref_uploaded: str | None = None
        if reference_image_path:
            ref = Path(reference_image_path)
            if not ref.is_file():
                raise FileNotFoundError(f"Reference image not found: {ref}")
            if not is_ipadapter_supported(arch):
                raise ValueError(f"IP-Adapter is not supported for architecture {arch}")
            ref_uploaded = self.comfy.upload_image(ref)

        if ref_uploaded:
            workflow = build_controlnet_ipadapter_txt2img_workflow(
                checkpoint=ckpt,
                positive=full_prompt,
                negative=neg,
                guide_image_filename=uploaded,
                ipadapter_image_filename=ref_uploaded,
                width=w,
                height=h,
                seed=seed,
                steps=st,
                cfg=cfg_scale,
                sampler=sampler,
                scheduler=scheduler,
                loras=merged_loras,
                depth_controlnet_file=cn_files["depth"],
                canny_controlnet_file=cn_files["canny"],
                depth_strength=float(depth_strength),
                canny_strength=float(canny_strength),
                canny_low_threshold=float(canny_low_threshold),
                canny_high_threshold=float(canny_high_threshold),
                ipadapter_weight=float(ipadapter_weight),
                ipadapter_weight_type=ipadapter_weight_type,
                ipadapter_ref_size=int(ipadapter_ref_size),
            )
        else:
            workflow = build_controlnet_txt2img_workflow(
                checkpoint=ckpt,
                positive=full_prompt,
                negative=neg,
                guide_image_filename=uploaded,
                width=w,
                height=h,
                seed=seed,
                steps=st,
                cfg=cfg_scale,
                sampler=sampler,
                scheduler=scheduler,
                loras=merged_loras,
                depth_controlnet_file=cn_files["depth"],
                canny_controlnet_file=cn_files["canny"],
                depth_strength=float(depth_strength),
                canny_strength=float(canny_strength),
                canny_low_threshold=float(canny_low_threshold),
                canny_high_threshold=float(canny_high_threshold),
            )

        face_detail_info = self._apply_face_detail_if_requested(
            workflow,
            use_face_detail=use_face_detail,
            flux2=flux2,
            defaults=defaults,
            cfg_scale=cfg_scale,
            sampler_name=sampler,
            scheduler_name=scheduler,
        )

        prompt_id, outputs, saved = self._queue_workflow_and_save(workflow)

        mode = "controlnet_ipadapter_txt2img" if ref_uploaded else "controlnet_txt2img"
        result = {
            "backend": "comfyui",
            "mode": mode,
            "guide_image": str(guide),
            "reference_image": reference_image_path,
            "ipadapter_weight": ipadapter_weight if ref_uploaded else None,
            "depth_strength": depth_strength,
            "canny_strength": canny_strength,
            "face_detail": face_detail_info,
            "architecture": arch,
            "controlnet_files": cn_files,
            "checkpoint_architecture": arch_check,
            "style": resolved_style,
            "checkpoint": ckpt,
            "prompt": full_prompt,
            "negative_prompt": neg,
            "width": w,
            "height": h,
            "steps": st,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if clamped:
            result["clamped_to_limits"] = clamped
        if arch_check.get("mismatch"):
            result["architecture_warning"] = arch_check.get("warnings")
        return result

    def extract_control_maps(
        self,
        *,
        image_path: str,
        maps: list[str] | None = None,
        resolution: int | None = None,
    ) -> dict[str, Any]:
        """Run OpenPose / Canny / lineart preprocessors on an image; save preview PNGs."""
        from studio.pose_control import PREPROCESSORS, build_preprocess_workflow
        from studio.ip_adapter_assets import image_dimensions

        src = Path(image_path)
        if not src.is_file():
            raise FileNotFoundError(f"Image not found: {src}")

        selected = maps or ["openpose", "canny", "anime_lineart"]
        for name in selected:
            if name not in PREPROCESSORS:
                raise ValueError(f"Unknown map {name!r}. Choose from {list(PREPROCESSORS)}")

        w, h = image_dimensions(src)
        res = resolution or max(w, h)
        uploaded = self.comfy.upload_image(src)
        saved_all: list[str] = []
        outputs_by_map: dict[str, list[str]] = {}

        for name in selected:
            workflow = build_preprocess_workflow(
                image_filename=uploaded,
                preprocessor=name,
                resolution=res,
            )
            prompt_id = self.comfy.queue_prompt(workflow)
            history = self.comfy.wait_for_completion(prompt_id)
            files = self.comfy.collect_outputs(history)
            paths: list[str] = []
            for file_info in files:
                local = self.comfy.download_file(file_info, self.output_dir)
                paths.append(str(local))
                saved_all.append(str(local))
            outputs_by_map[name] = paths

        return {
            "backend": "comfyui",
            "mode": "extract_control_maps",
            "image_path": str(src),
            "resolution": res,
            "maps": outputs_by_map,
            "saved_files": saved_all,
        }

    def generate_image_pose_guided(
        self,
        *,
        image_path: str,
        pose_image_path: str,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        seed: int | None = None,
        denoising_strength: float = 0.38,
        openpose_strength: float = 0.82,
        preprocess_pose: bool = False,
        sampler: str | None = None,
        scheduler: str | None = None,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        """I2i with SDXL OpenPose ControlNet — identity from image_path, pose from pose_image_path."""
        from studio.pose_control import OPENPOSE_CONTROLNET_ASSET, build_openpose_i2i_workflow

        ctx = self._resolve_generation_context(
            style=style,
            prompt=prompt,
            negative_prompt=negative_prompt,
            loras=loras,
            content_rating=content_rating,
        )
        style_cfg = ctx["style_cfg"]
        resolved_style = ctx["resolved_style"]
        ckpt = ctx["ckpt"]
        full_prompt = ctx["full_prompt"]
        neg = ctx["neg"]
        defaults = ctx["defaults"]
        merged_loras = ctx["merged_loras"]

        src = Path(image_path)
        pose = Path(pose_image_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source image not found: {src}")
        if not pose.is_file():
            raise FileNotFoundError(f"Pose image not found: {pose}")

        w = width or defaults.get("width", 1024)
        h = height or defaults.get("height", 1024)
        st = steps or defaults.get("steps", 28)
        limits = self.hardware_context().get("generation_limits", {})
        w, h, st, clamped = clamp_image_params(w, h, st, limits)
        cfg_scale = cfg if cfg is not None else defaults.get("cfg", 5.5)
        sampler_name = sampler or defaults.get("sampler", "euler_ancestral")
        scheduler_name = scheduler or defaults.get("scheduler", "normal")

        uploaded = self.comfy.upload_image(src)
        pose_uploaded = self.comfy.upload_image(pose)

        if self.pick_backend(backend) == "invoke":
            raise NotImplementedError("Pose-guided i2i requires ComfyUI.")

        workflow = build_openpose_i2i_workflow(
            checkpoint=ckpt,
            positive=full_prompt,
            negative=neg,
            source_image_filename=uploaded,
            pose_image_filename=pose_uploaded,
            width=w,
            height=h,
            openpose_controlnet_file=OPENPOSE_CONTROLNET_ASSET["filename"],
            openpose_strength=float(openpose_strength),
            preprocess_pose=bool(preprocess_pose),
            pose_resolution=max(w, h),
            seed=seed,
            steps=st,
            cfg=cfg_scale,
            sampler=sampler_name,
            scheduler=scheduler_name,
            denoising_strength=float(denoising_strength),
            loras=merged_loras,
        )

        prompt_id, outputs, saved = self._queue_workflow_and_save(workflow)
        result = {
            "backend": "comfyui",
            "mode": "pose_guided_i2i",
            "image_path": str(src),
            "pose_image_path": str(pose),
            "preprocess_pose": preprocess_pose,
            "openpose_strength": openpose_strength,
            "denoising_strength": denoising_strength,
            "style": resolved_style,
            "prompt": full_prompt,
            "negative_prompt": neg,
            "width": w,
            "height": h,
            "steps": st,
            "loras": merged_loras or None,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if clamped:
            result["clamped_to_limits"] = clamped
        return result

    def edit_image(
        self,
        *,
        image_path: str,
        instruction: str,
        food_group: str | None = None,
        style: str | None = None,
        mode: str = "auto",
        segment_prompt: str = "",
        mask_region: str = "",
        negative_prompt: str | None = None,
        reference_image_path: str | None = None,
        flag_reference: str = "",
        seed: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        denoising_strength: float = 1.0,
        ipadapter_weight: float = 0.85,
        depth_strength: float = 0.52,
        canny_strength: float = 0.62,
        preserve_subject: bool = True,
        run_verification: bool = True,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        """
        Unified image edit: classifies intent and runs i2i, inpaint, ControlNet, or hybrid pipeline.
        food_group: anime | fantasy | cyberpunk | photoreal (four art food groups).
        """
        plan = plan_edit(
            instruction=instruction,
            food_group=food_group,
            mode=mode,
            segment_prompt=segment_prompt,
            preserve_subject=preserve_subject,
        )
        resolved_style, architecture = resolve_style_for_edit(
            food_group=food_group or plan.get("food_group"),
            style=style,
            architecture=None,
            catalog=self.catalog,
        )

        prompt_add, neg_add = enrich_edit_prompts(instruction, food_group or plan.get("food_group"))
        merged_neg = f"{negative_prompt}, {neg_add}" if negative_prompt else neg_add

        pipeline = plan["pipeline"]
        stages: list[dict[str, Any]] = []
        src = Path(image_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source image not found: {src}")

        working_image = str(src)

        if pipeline == "i2i":
            result = self.generate_image_i2i(
                image_path=working_image,
                prompt=prompt_add,
                style=resolved_style,
                negative_prompt=merged_neg,
                seed=seed,
                steps=steps,
                cfg=cfg,
                denoising_strength=plan.get("denoise_i2i") or 0.35,
                backend=backend,
                content_rating=content_rating,
            )
            stages.append({"stage": "i2i", "result": result})
            out = {**result, "edit_plan": plan, "food_group": plan.get("food_group"), "stages": stages}

        elif pipeline == "controlnet":
            result = self.generate_image_controlnet(
                guide_image_path=working_image,
                prompt=prompt_add,
                style=resolved_style,
                negative_prompt=merged_neg,
                seed=seed,
                steps=steps,
                cfg=cfg,
                depth_strength=depth_strength,
                canny_strength=canny_strength,
                backend=backend,
                content_rating=content_rating,
            )
            stages.append({"stage": "controlnet", "result": result})
            out = {**result, "edit_plan": plan, "food_group": plan.get("food_group"), "stages": stages}

        else:
            # hybrid_preserve (default) or hybrid: inpaint on original or after controlnet base
            if pipeline == "hybrid" and plan.get("use_controlnet"):
                base = self.generate_image_controlnet(
                    guide_image_path=working_image,
                    prompt=prompt_add,
                    style=resolved_style,
                    negative_prompt=merged_neg,
                    seed=seed,
                    steps=steps,
                    cfg=cfg,
                    depth_strength=depth_strength,
                    canny_strength=canny_strength,
                    backend=backend,
                    content_rating=content_rating,
                )
                stages.append({"stage": "controlnet_base", "result": base})
                files = base.get("saved_files") or []
                if not files:
                    raise RuntimeError("ControlNet base stage produced no output files")
                working_image = files[-1]

            mask_path: str | None = None
            effective_region = mask_region or plan.get("mask_region_fallback") or "right_building"
            seg_prompt = plan.get("segment_prompt") or segment_prompt
            if seg_prompt:
                mask_local, fallback_region = segment_image_to_mask(
                    self.comfy,
                    self.output_dir,
                    image_path=Path(working_image),
                    segment_prompt=seg_prompt,
                )
                if mask_local and mask_local.is_file():
                    mask_path = str(mask_local)
                    stages.append({"stage": "segment", "segment_prompt": seg_prompt, "mask_path": mask_path})
                else:
                    effective_region = fallback_region
                    stages.append({"stage": "segment_fallback", "mask_region": effective_region})

            flag_ref = flag_reference or ""
            if not flag_ref and plan.get("flag_reference"):
                flag_ref = str(plan["flag_reference"]).replace("_flag", "")
            if not is_ipadapter_supported(architecture):
                flag_ref = ""
                reference_image_path = None

            if pipeline in {"hybrid", "hybrid_preserve", "inpaint"}:
                result = self.inpaint_advanced(
                    image_path=working_image,
                    prompt=prompt_add,
                    reference_image_path=reference_image_path,
                    flag_reference=flag_ref,
                    mask_path=mask_path,
                    mask_region=effective_region if not mask_path else "none",
                    style=resolved_style,
                    negative_prompt=merged_neg,
                    seed=seed,
                    steps=steps,
                    cfg=cfg,
                    denoising_strength=denoising_strength,
                    ipadapter_weight=ipadapter_weight,
                    backend=backend,
                    content_rating=content_rating,
                )
            else:
                result = self.inpaint_image(
                    image_path=working_image,
                    prompt=prompt_add,
                    style=resolved_style,
                    negative_prompt=merged_neg,
                    seed=seed,
                    steps=steps,
                    cfg=cfg,
                    denoising_strength=denoising_strength,
                    backend=backend,
                    content_rating=content_rating,
                )
            stages.append({"stage": "inpaint", "result": result})
            out = {
                **result,
                "mode": "edit_hybrid" if pipeline.startswith("hybrid") else "edit_inpaint",
                "edit_plan": plan,
                "food_group": plan.get("food_group"),
                "style": resolved_style,
                "architecture": architecture,
                "stages": stages,
            }

        if run_verification:
            out["verification"] = verify_edit_result(
                instruction=instruction,
                plan=plan,
                result=out,
            )
        out["art_food_groups"] = ART_FOOD_GROUPS
        return out

    def generate_image_i2i(
        self,
        *,
        image_path: str,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        checkpoint: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        seed: int | None = None,
        denoising_strength: float = 0.45,
        sampler: str | None = None,
        scheduler: str | None = None,
        face_detail: bool | None = None,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        """Image-to-image refinement using an existing image as starting point (denoising < 1.0)."""
        ctx = self._resolve_generation_context(
            style=style,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            loras=loras,
            content_rating=content_rating,
        )
        rating = ctx["rating"]
        style_cfg = ctx["style_cfg"]
        resolved_style = ctx["resolved_style"]
        ckpt = ctx["ckpt"]
        full_prompt = ctx["full_prompt"]
        neg = ctx["neg"]
        defaults = ctx["defaults"]
        merged_loras = ctx["merged_loras"]

        w = width or defaults.get("width", 1024)
        h = height or defaults.get("height", 1024)
        st = steps or defaults.get("steps", 28)
        limits = self.hardware_context().get("generation_limits", {})
        w, h, st, clamped = clamp_image_params(w, h, st, limits)
        cfg_scale = cfg if cfg is not None else defaults.get("cfg", 7.0)
        sampler_name = sampler or defaults.get("sampler", "euler_ancestral")
        scheduler_name = scheduler or defaults.get("scheduler", "normal")
        denoise = float(denoising_strength)
        use_face_detail = (
            face_detail if face_detail is not None else bool(defaults.get("face_detail", False))
        )

        # Upload source image
        src = Path(image_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source image not found: {src}")
        uploaded = self.comfy.upload_image(src)

        chosen = self.pick_backend(backend)

        if chosen == "invoke":
            raise NotImplementedError("I2I is only supported on ComfyUI backend for now.")

        workflow = build_i2i_workflow(
            checkpoint=ckpt,
            positive=full_prompt,
            negative=neg,
            image_filename=uploaded,
            width=w,
            height=h,
            seed=seed,
            steps=st,
            cfg=cfg_scale,
            sampler=sampler_name,
            scheduler=scheduler_name,
            denoising_strength=denoise,
            loras=merged_loras,
        )

        flux2 = style_cfg.get("architecture") in {"flux2", "flux2_klein"} or is_flux_checkpoint(ckpt)
        face_detail_info = self._apply_face_detail_if_requested(
            workflow,
            use_face_detail=use_face_detail,
            flux2=flux2,
            defaults=defaults,
            cfg_scale=cfg_scale,
            sampler_name=sampler_name,
            scheduler_name=scheduler_name,
        )

        prompt_id, outputs, saved = self._queue_workflow_and_save(workflow)

        result = {
            "backend": "comfyui",
            "mode": "i2i",
            "image_path": str(src),
            "uploaded_image": uploaded,
            "denoising_strength": denoise,
            "prompt": full_prompt,
            "negative_prompt": neg,
            "width": w,
            "height": h,
            "steps": st,
            "cfg": cfg_scale,
            "sampler": sampler_name,
            "scheduler": scheduler_name,
            "loras": merged_loras or None,
            "face_detail": face_detail_info,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if clamped:
            result["clamped_to_limits"] = clamped
        return result

    def inpaint_image(
        self,
        *,
        image_path: str,
        prompt: str,
        style: str | None = None,
        negative_prompt: str | None = None,
        checkpoint: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        seed: int | None = None,
        denoising_strength: float = 0.35,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        """Inpainting-style edit focused on background / specific areas while protecting the main subject."""
        ctx = self._resolve_generation_context(
            style=style,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            loras=loras,
            content_rating=content_rating,
        )
        rating = ctx["rating"]
        style_cfg = ctx["style_cfg"]
        resolved_style = ctx["resolved_style"]
        ckpt = ctx["ckpt"]
        full_prompt = ctx["full_prompt"]
        neg = ctx["neg"]
        defaults = ctx["defaults"]
        merged_loras = ctx["merged_loras"]

        w = width or defaults.get("width", 1024)
        h = height or defaults.get("height", 1024)
        st = steps or defaults.get("steps", 25)
        limits = self.hardware_context().get("generation_limits", {})
        w, h, st, clamped = clamp_image_params(w, h, st, limits)
        cfg_scale = cfg if cfg is not None else defaults.get("cfg", 5.0)
        denoise = float(denoising_strength)

        # Upload source image
        src = Path(image_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source image not found: {src}")
        uploaded = self.comfy.upload_image(src)

        chosen = self.pick_backend(backend)

        if chosen == "invoke":
            raise NotImplementedError("Inpainting is only supported on ComfyUI backend for now.")

        workflow = build_inpaint_workflow(
            checkpoint=ckpt,
            positive=full_prompt,
            negative=neg,
            image_filename=uploaded,
            width=w,
            height=h,
            seed=seed,
            steps=st,
            cfg=cfg_scale,
            denoising_strength=denoise,
            loras=merged_loras,
        )

        prompt_id, outputs, saved = self._queue_workflow_and_save(workflow)

        result = {
            "backend": "comfyui",
            "mode": "inpaint",
            "image_path": str(src),
            "uploaded_image": uploaded,
            "denoising_strength": denoise,
            "prompt": full_prompt,
            "negative_prompt": neg,
            "width": w,
            "height": h,
            "steps": st,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if clamped:
            result["clamped_to_limits"] = clamped
        return result

    def inpaint_advanced(
        self,
        *,
        image_path: str,
        prompt: str,
        reference_image_path: str | None = None,
        flag_reference: str = "",
        mask_path: str | None = None,
        mask_region: str = "church_tower",
        style: str | None = None,
        negative_prompt: str | None = None,
        checkpoint: str | None = None,
        loras: list[dict[str, Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        steps: int | None = None,
        cfg: float | None = None,
        seed: int | None = None,
        denoising_strength: float = 0.55,
        ipadapter_weight: float = 0.85,
        ipadapter_ref_size: int = 256,
        use_controlnet_depth: bool = False,
        controlnet_depth_strength: float = 0.75,
        backend: str | None = None,
        content_rating: str | None = None,
    ) -> dict[str, Any]:
        """
        Advanced inpainting with optional IP-Adapter reference image.
        Best tool for adding new objects (flags, signs, etc.) while preserving the subject.
        """
        ctx = self._resolve_generation_context(
            style=style,
            prompt=prompt,
            negative_prompt=negative_prompt,
            checkpoint=checkpoint,
            loras=loras,
            content_rating=content_rating,
        )
        rating = ctx["rating"]
        style_cfg = ctx["style_cfg"]
        resolved_style = ctx["resolved_style"]
        ckpt = ctx["ckpt"]
        full_prompt = ctx["full_prompt"]
        neg = ctx["neg"]
        defaults = ctx["defaults"]
        merged_loras = ctx["merged_loras"]

        w = width or defaults.get("width", 1024)
        h = height or defaults.get("height", 1024)
        st = steps or defaults.get("steps", 28)
        limits = self.hardware_context().get("generation_limits", {})
        w, h, st, clamped = clamp_image_params(w, h, st, limits)
        cfg_scale = cfg if cfg is not None else defaults.get("cfg", 5.0)

        src = Path(image_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source image not found: {src}")
        uploaded = self.comfy.upload_image(src)

        ref_path: Path | None = None
        if reference_image_path:
            candidate = Path(reference_image_path)
            if candidate.is_file():
                ref_path = candidate
        elif flag_reference.lower() in {"ireland", "irish", "ireland_flag"}:
            ref_path = Path(default_flag_reference_path(self.cfg))
        elif flag_reference.lower() in {"usa", "us", "american", "usa_flag"}:
            ref_path = ensure_extended_reference(self.cfg, "usa_flag")
        elif flag_reference.lower() in {"uk", "british", "uk_flag"}:
            ref_path = ensure_extended_reference(self.cfg, "uk_flag")

        ref_uploaded = self.comfy.upload_image(ref_path) if ref_path else None

        mask_uploaded = None
        effective_mask_region = mask_region
        if effective_mask_region.lower() in {"top", "sky", "church"}:
            effective_mask_region = "church_tower"
        if mask_path:
            mp = Path(mask_path)
            if mp.is_file():
                mask_uploaded = self.comfy.upload_image(mp)
        elif effective_mask_region and effective_mask_region.lower() not in {"none", "off", ""}:
            mw, mh = image_dimensions(src)
            mask_file = self.output_dir / f"_mask_{seed or 0}_{effective_mask_region}.png"
            write_region_mask_png(mask_file, mw, mh, region=effective_mask_region)
            mask_uploaded = self.comfy.upload_image(mask_file)

        chosen = self.pick_backend(backend)
        if chosen == "invoke":
            raise NotImplementedError("Advanced inpainting is only supported on ComfyUI.")

        sampler = defaults.get("sampler", "dpmpp_2m")
        scheduler = defaults.get("scheduler", "karras")

        workflow = build_advanced_inpaint_workflow(
            checkpoint=ckpt,
            positive=full_prompt,
            negative=neg,
            image_filename=uploaded,
            mask_filename=mask_uploaded,
            ipadapter_image_filename=ref_uploaded,
            width=w,
            height=h,
            seed=seed,
            steps=st,
            cfg=cfg_scale,
            denoising_strength=float(denoising_strength),
            loras=merged_loras,
            ipadapter_weight=float(ipadapter_weight),
            ipadapter_weight_type="composition",
            ipadapter_ref_size=int(ipadapter_ref_size),
            sampler=sampler,
            scheduler=scheduler,
            use_controlnet_depth=use_controlnet_depth,
            controlnet_depth_strength=float(controlnet_depth_strength),
        )

        prompt_id, outputs, saved = self._queue_workflow_and_save(workflow)

        result = {
            "backend": "comfyui",
            "mode": "inpaint_advanced",
            "image_path": str(src),
            "reference_image": str(ref_path) if ref_path else reference_image_path,
            "mask_region": mask_region if mask_uploaded else None,
            "denoising_strength": denoising_strength,
            "ipadapter_weight": ipadapter_weight,
            "prompt": full_prompt,
            "negative_prompt": neg,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if clamped:
            result["clamped_to_limits"] = clamped
        return result

    def _resolve_i2v_workflow(
        self,
        *,
        mode: str,
        workflow_id: str | None,
        limits: dict[str, Any],
        profile: dict[str, Any],
    ) -> tuple[str | None, bool]:
        """
        Pick catalog workflow key and whether to use the Wan 2.1 14B i2v_gpu builder.

        Default I2V (empty workflow_id): catalog `i2v_5b` (Wan 2.2 TI2V-5B native).
        Default V2V (empty workflow_id): catalog `v2v_5b_painter`.
        Explicit `workflow_id=i2v`: legacy 14B dual-model blockswap workflow.
        Explicit `workflow_id=i2v_gpu`: Wan 2.1 14B builder (24GB+ or forced).
        """
        wf_choice = (workflow_id or "").strip().lower()

        if mode == "v2v":
            if wf_choice in {"v2v_5b", "v2v_5b_painter"}:
                return wf_choice, False
            if wf_choice in {"i2v_5b", "i2v_5b_painter"}:
                return wf_choice.replace("i2v", "v2v", 1), False
            return "v2v_5b_painter", False

        if mode != "i2v":
            return workflow_id, False

        caps = limits.get("video_i2v", {})
        default_wf = str(caps.get("workflow_id") or "i2v_5b")

        if wf_choice == "i2v_gpu":
            return "i2v_gpu", True
        if wf_choice == "i2v_wan21":
            return "i2v_wan21", False
        if wf_choice == "i2v":
            return "i2v", False
        if wf_choice in {"i2v_5b", "i2v_5b_painter"}:
            return wf_choice, False
        if wf_choice in {"t2v", "t2v_wan22"}:
            return wf_choice, False
        return default_wf, False

    def load_ui_workflow(
        self,
        workflow_id: str | None,
        mode: str = "t2v",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load a Stability Matrix UI-format workflow JSON and its catalog metadata."""
        wf_meta = self.catalog.resolve_video_workflow(workflow_id, mode)
        workflows_dir = Path(self.cfg["stability_matrix"]["workflows"])
        wf_path = workflows_dir / wf_meta["file"]
        if not wf_path.exists():
            raise FileNotFoundError(f"Workflow not found: {wf_path}")
        cache_key = (str(wf_path), wf_path.stat().st_mtime)
        cached = self._workflow_ui_cache.get(cache_key)
        if cached is not None:
            return cached, wf_meta
        with wf_path.open(encoding="utf-8") as f:
            ui = json.load(f)
        self._workflow_ui_cache[cache_key] = ui
        return ui, wf_meta

    def generate_video(
        self,
        *,
        prompt: str,
        mode: str = "t2v",
        style: str | None = None,
        negative_prompt: str | None = None,
        workflow_id: str | None = None,
        content_rating: str | None = None,
        image_path: str | None = None,
        video_path: str | None = None,
        concat_source: bool = True,
        num_frames: int | None = None,
        frame_rate: float | None = None,
        loras: list[dict[str, Any]] | None = None,
        lora_ids: list[str] | None = None,
        lora_bundle: str = "",
        use_painter_i2v: bool = False,
        motion_amplitude: float = 1.15,
        smooth_motion: bool = False,
    ) -> dict[str, Any]:
        if not self.comfy.is_running():
            raise RuntimeError("ComfyUI must be running for video generation.")

        from studio.gpu_backend import acquire_gpu_lock, assert_backend_available, release_gpu_lock

        assert_backend_available(
            self.cfg,
            "comfyui",
            comfyui_running=True,
            operation="generate_video",
        )
        acquire_gpu_lock(self.cfg, "comfyui", detail=f"generate_video mode={mode}")
        try:
            return self._generate_video_impl(
                prompt=prompt,
                mode=mode,
                style=style,
                negative_prompt=negative_prompt,
                workflow_id=workflow_id,
                content_rating=content_rating,
                image_path=image_path,
                video_path=video_path,
                concat_source=concat_source,
                num_frames=num_frames,
                frame_rate=frame_rate,
                loras=loras,
                lora_ids=lora_ids,
                lora_bundle=lora_bundle,
                use_painter_i2v=use_painter_i2v,
                motion_amplitude=motion_amplitude,
                smooth_motion=smooth_motion,
            )
        finally:
            release_gpu_lock(self.cfg, "comfyui")

    def _generate_video_impl(
        self,
        *,
        prompt: str,
        mode: str = "t2v",
        style: str | None = None,
        negative_prompt: str | None = None,
        workflow_id: str | None = None,
        content_rating: str | None = None,
        image_path: str | None = None,
        video_path: str | None = None,
        concat_source: bool = True,
        num_frames: int | None = None,
        frame_rate: float | None = None,
        loras: list[dict[str, Any]] | None = None,
        lora_ids: list[str] | None = None,
        lora_bundle: str = "",
        use_painter_i2v: bool = False,
        motion_amplitude: float = 1.15,
        smooth_motion: bool = False,
    ) -> dict[str, Any]:
        rating = content_rating or self.cfg.get("default_content_rating", "open")
        original_mode = (mode or "t2v").lower().strip()
        quality_preset: dict[str, Any] = {}
        mode = original_mode
        source_video: Path | None = None
        v2v_seed_frame: Path | None = None

        if mode == "v2v":
            if not video_path:
                raise ValueError("video_path is required for mode=v2v (path to the source clip).")
            source_video = Path(video_path)
            if not source_video.is_file():
                raise FileNotFoundError(f"Source video not found: {source_video}")
            v2v_seed_frame = self.output_dir / f"v2v_seed_{source_video.stem}.png"
            extract_last_frame(source_video, v2v_seed_frame)
            image_path = str(v2v_seed_frame)
            mode = "i2v"

        if mode == "i2v" and not image_path:
            raise ValueError("image_path is required for mode=i2v (path to the source image).")

        hw_ctx = self.hardware_context()
        limits = hw_ctx.get("generation_limits", {})
        profile = hw_ctx.get("hardware_profile", {})

        clamp_mode_early = original_mode if original_mode == "v2v" else mode
        caps_key = "video_i2v" if clamp_mode_early in {"i2v", "v2v"} else "video_t2v"
        caps = limits.get(caps_key, {})
        nf_work = num_frames if num_frames is not None else int(caps.get("max_frames", 65))
        fr_work = frame_rate if frame_rate is not None else float(caps.get("frame_rate", 16))

        smooth_motion, lora_bundle, lora_ids, motion_amplitude, nf_work, fr_work, safety_applied = (
            apply_video_safety_caps(
                vram_gb=float(profile.get("vram_gb") or 16),
                vram_free_gb=profile.get("vram_free_gb"),
                smooth_motion=smooth_motion,
                lora_bundle=lora_bundle,
                lora_ids=lora_ids,
                use_painter_i2v=use_painter_i2v,
                workflow_id=workflow_id,
                num_frames=nf_work,
                frame_rate=fr_work,
                motion_amplitude=motion_amplitude,
            )
        )
        num_frames = nf_work
        frame_rate = fr_work

        if smooth_motion and original_mode in {"i2v", "v2v"}:
            motion_amplitude, frame_rate, lora_bundle, lora_ids, quality_preset = apply_smooth_motion_preset(
                smooth_motion=True,
                motion_amplitude=motion_amplitude,
                frame_rate=frame_rate,
                lora_bundle=lora_bundle,
                lora_ids=lora_ids,
                vram_gb=float(profile.get("vram_gb") or 16),
            )
            use_painter_i2v = True
            if quality_preset.get("extra_negative"):
                extra = quality_preset["extra_negative"]
                negative_prompt = f"{negative_prompt}, {extra}" if negative_prompt else extra
        clamp_mode = original_mode if original_mode == "v2v" else mode
        num_frames, frame_rate, video_clamped = clamp_video_params(
            mode=clamp_mode,
            num_frames=num_frames,
            frame_rate=frame_rate,
            limits=limits,
        )

        if profile.get("prefer_prompt_quality"):
            if ANATOMY_POSITIVE_HINT not in prompt:
                prompt = f"{prompt}, {ANATOMY_POSITIVE_HINT}"
            if not negative_prompt:
                negative_prompt = ANATOMY_NEGATIVE_HINT
            elif ANATOMY_NEGATIVE_HINT not in negative_prompt:
                negative_prompt = f"{negative_prompt}, {ANATOMY_NEGATIVE_HINT}"

        wf_key, use_gpu_i2v = self._resolve_i2v_workflow(
            mode=original_mode if original_mode == "v2v" else mode,
            workflow_id=workflow_id,
            limits=limits,
            profile=profile,
        )
        if use_gpu_i2v:
            ui_workflow, wf_meta = self.load_ui_workflow("t2v", "t2v")
        else:
            ui_workflow, wf_meta = self.load_ui_workflow(
                wf_key or workflow_id,
                "v2v" if original_mode == "v2v" else mode,
            )
            if not wf_key:
                wf_key = (
                    self.catalog._find_video_workflow_key(workflow_id)
                    if workflow_id
                    else next(
                        (
                            k
                            for k, wf in self.catalog.video_workflows.items()
                            if wf.get("file") == wf_meta.get("file")
                        ),
                        None,
                    )
                )

        style_cfg = self.catalog.resolve_style(style) if style else {}
        prefix = style_cfg.get("prompt_prefix", "")
        base_neg = negative_prompt or style_cfg.get("negative_prompt", "")
        full_prompt, neg = apply_content_policy(
            prompt=prompt,
            positive_prefix=prefix,
            negative_prompt=base_neg,
            content_rating=rating,
        )

        uploaded_image: str | None = None
        if image_path:
            src = Path(image_path)
            if not src.is_file():
                raise FileNotFoundError(f"Source image not found: {src}")
            uploaded_image = self.comfy.upload_image(src)
            if use_gpu_i2v:
                ui_workflow = build_wan21_i2v_ui_workflow(
                    ui_workflow,
                    image_filename=uploaded_image,
                    limits=limits,
                    num_frames=num_frames,
                    frame_rate=frame_rate,
                    gpu_only=bool(profile.get("gpu_only", True)),
                )
            else:
                painter = use_painter_i2v or wf_key in {"i2v_5b_painter", "v2v_5b_painter"}
                caps = limits.get("video_i2v", {})
                max_w = int(caps.get("max_width", 480))
                max_h = int(caps.get("max_height", 640))
                # PainterI2V VAE-encodes the full frame sequence — keep 480×832 for sane runtime.
                if painter:
                    max_w, max_h = min(max_w, 480), min(max_h, 832)
                try:
                    from PIL import Image

                    with Image.open(src) as im:
                        vid_w, vid_h = fit_i2v_dimensions(im.width, im.height, max_w, max_h)
                except Exception:
                    vid_w, vid_h = max_w, max_h
                native_i2v = wf_key in {
                    "i2v_5b",
                    "i2v_5b_painter",
                    "v2v_5b",
                    "v2v_5b_painter",
                } or "Wan22ImageToVideoLatent" in {
                    n.get("type") for n in ui_workflow.get("nodes", [])
                }
                if native_i2v:
                    smooth_steps = quality_preset.get("sampler_steps")
                    smooth_cfg = quality_preset.get("sampler_cfg")
                    ui_workflow = inject_i2v_native_quality(
                        ui_workflow,
                        steps=int(smooth_steps) if smooth_steps else (30 if painter else 40),
                        cfg=float(smooth_cfg) if smooth_cfg else 5.5,
                    )
                ui_workflow = inject_i2v_ui_workflow(
                    ui_workflow,
                    image_filename=uploaded_image,
                    num_frames=num_frames,
                    frame_rate=frame_rate,
                    width=vid_w,
                    height=vid_h,
                )
                resolved_loras = loras if loras is not None else resolve_lora_list(lora_ids, bundle=lora_bundle)
                if resolved_loras or painter:
                    ui_workflow = inject_i2v_enhancements_ui_workflow(
                        ui_workflow,
                        loras=resolved_loras,
                        use_painter_i2v=painter,
                        motion_amplitude=motion_amplitude,
                        width=vid_w,
                        height=vid_h,
                        num_frames=num_frames,
                    )

        ui_workflow = inject_prompts_ui_workflow(
            ui_workflow,
            positive=full_prompt,
            negative=neg,
            prompt_nodes=wf_meta.get("prompt_nodes"),
        )

        object_info = self.comfy.get_object_info()
        api_workflow = ui_to_api(ui_workflow, object_info=object_info)
        prompt_id = self.comfy.queue_prompt(api_workflow)
        old_timeout = self.comfy.timeout
        painter_run = use_painter_i2v or wf_key in {"i2v_5b_painter", "v2v_5b_painter"}
        try:
            self.comfy.timeout = max(old_timeout, 3600 if painter_run else 1200)
            history = self.comfy.wait_for_completion(prompt_id)
        finally:
            self.comfy.timeout = old_timeout
        outputs = self.comfy.collect_outputs(history)
        saved = self._save_comfy_outputs(
            outputs,
            extensions=(".mp4", ".webm", ".gif", ".png", ".jpg"),
        )

        if source_video and concat_source and saved:
            extended = self.output_dir / f"{source_video.stem}_v2v_extended.mp4"
            concat_videos([source_video, Path(saved[0])], extended)
            saved.append(str(extended))

        result = {
            "backend": "comfyui",
            "mode": original_mode,
            "workflow_id": wf_key,
            "workflow": wf_meta.get("file"),
            "prompt": full_prompt,
            "negative_prompt": neg,
            "image_path": image_path,
            "video_path": str(source_video) if source_video else None,
            "v2v_seed_frame": str(v2v_seed_frame) if v2v_seed_frame else None,
            "concat_source": bool(source_video and concat_source),
            "uploaded_image": uploaded_image,
            "num_frames": num_frames,
            "frame_rate": frame_rate,
            "use_painter_i2v": use_painter_i2v or wf_key in {"i2v_5b_painter", "v2v_5b_painter"},
            "motion_amplitude": motion_amplitude
            if (use_painter_i2v or wf_key in {"i2v_5b_painter", "v2v_5b_painter"})
            else None,
            "smooth_motion": smooth_motion,
            "quality_preset": quality_preset or None,
            "loras": loras
            if loras is not None
            else resolve_lora_list(lora_ids, bundle=lora_bundle) or None,
            "prompt_id": prompt_id,
            "outputs": outputs,
            "saved_files": saved,
        }
        if video_clamped:
            result["clamped_to_limits"] = video_clamped
        if safety_applied:
            result["applied_safety_caps"] = safety_applied
        if original_mode in {"t2v", "i2v", "v2v"} and not saved:
            raise RuntimeError(
                f"ComfyUI finished without video outputs (prompt_id={prompt_id}). "
                "Check ComfyUI for validation errors or a stuck queue."
            )
        return result

    def generate_audio(
        self,
        *,
        mode: str = "speech",
        text: str = "",
        prompt: str = "",
        instruction: str = "",
        language: str = "en",
        duration_seconds: float = 0.0,
        seed: int | None = None,
        filename_prefix: str = "",
    ) -> dict[str, Any]:
        """Generate speech, sound effects, or voice-design audio via MOSS-TTS in ComfyUI."""
        if not self.comfy.is_running():
            raise RuntimeError("ComfyUI must be running for audio generation.")

        from studio.gpu_backend import acquire_gpu_lock, assert_backend_available, release_gpu_lock

        assert_backend_available(
            self.cfg,
            "comfyui",
            comfyui_running=True,
            operation="generate_audio",
        )
        mode_key = (mode or "speech").lower().strip()
        acquire_gpu_lock(self.cfg, "comfyui", detail=f"generate_audio mode={mode_key}")
        try:
            if mode_key not in {"speech", "sound_effect", "voice_design"}:
                raise ValueError("mode must be speech, sound_effect, or voice_design")

            import random

            resolved_seed = int(seed if seed is not None else random.randint(0, 2**32 - 1))
            prefix = filename_prefix or f"audio/moss_{mode_key}"

            if mode_key == "speech":
                if not text.strip():
                    raise ValueError("text is required for mode=speech")
                workflow = build_moss_speech_workflow(
                    text=text.strip(),
                    language=language,
                    seed=resolved_seed,
                    filename_prefix=prefix,
                )
            elif mode_key == "sound_effect":
                sfx_prompt = (prompt or text).strip()
                if not sfx_prompt:
                    raise ValueError("prompt (or text) is required for mode=sound_effect")
                sfx_duration = duration_seconds if duration_seconds > 0 else 5.0
                workflow = build_moss_sound_effect_workflow(
                    prompt=sfx_prompt,
                    duration_seconds=sfx_duration,
                    seed=resolved_seed,
                    filename_prefix=prefix,
                )
            else:
                if not text.strip():
                    raise ValueError("text is required for mode=voice_design")
                if not instruction.strip():
                    raise ValueError("instruction is required for mode=voice_design (voice description)")
                voice_instruction = polish_voice_instruction(instruction.strip(), text.strip())
                if not voice_instruction:
                    raise ValueError(
                        "instruction must describe voice character only (age, tone, gender) — "
                        "not clip length or timing"
                    )
                duration_hint = duration_seconds if duration_seconds > 0 else None
                workflow = build_moss_voice_design_workflow(
                    text=text.strip(),
                    instruction=voice_instruction,
                    language=language,
                    seed=resolved_seed,
                    filename_prefix=prefix,
                    max_new_tokens=estimate_voice_max_tokens(
                        text.strip(), duration_seconds=duration_hint
                    ),
                    duration_seconds=duration_hint,
                )

            prompt_id = self.comfy.queue_prompt(workflow)
            old_timeout = self.comfy.timeout
            try:
                self.comfy.timeout = max(old_timeout, 1800)
                history = self.comfy.wait_for_completion(prompt_id)
            finally:
                self.comfy.timeout = old_timeout

            outputs = self.comfy.collect_outputs(history)
            saved = self._save_comfy_outputs(
                outputs,
                extensions=(".mp3", ".flac", ".wav", ".ogg"),
            )
            if not saved:
                raise RuntimeError(
                    f"ComfyUI finished without audio outputs (prompt_id={prompt_id}). "
                    "Ensure comfyui-moss-tts is installed and MOSS models are downloaded."
                )
            cleaned: list[str] = []
            for path_str in saved:
                path = Path(path_str)
                if path.suffix.lower() in {".mp3", ".wav", ".flac", ".ogg"}:
                    try:
                        trim_leading_trailing_silence(path, self.cfg)
                    except Exception:
                        pass
                cleaned.append(str(path))
            saved = cleaned
            saved, delivered = deliver_files(self.cfg, saved)
            voice_instruction = (
                polish_voice_instruction(instruction.strip(), text.strip())
                if mode_key == "voice_design" and instruction
                else None
            )
            return {
                "backend": "comfyui",
                "mode": mode_key,
                "text": text or None,
                "prompt": prompt or None,
                "instruction": voice_instruction if mode_key == "voice_design" else (instruction or None),
                "language": language,
                "duration_seconds": (
                    (duration_seconds if duration_seconds > 0 else 5.0) if mode_key == "sound_effect"
                    else (duration_seconds if duration_seconds > 0 else None)
                ),
                "seed": resolved_seed,
                "prompt_id": prompt_id,
                "outputs": outputs,
                "saved_files": saved,
                "delivered_files": delivered,
            }
        finally:
            release_gpu_lock(self.cfg, "comfyui")

    def generate_video_hero(
        self,
        *,
        prompt: str,
        image_path: str,
        negative_prompt: str = "",
        video_length: int = 49,
        resolution: str = "832x480",
        seed: int = -1,
        motion_amplitude: float = 1.05,
        model_type: str = "i2v_2_2_Enhanced_Lightning_v2",
    ) -> dict[str, Any]:
        from studio.wan2gp_runner import generate_video_hero as run_hero

        return run_hero(
            self.cfg,
            prompt=prompt,
            image_path=image_path,
            negative_prompt=negative_prompt,
            video_length=video_length,
            resolution=resolution,
            seed=seed,
            motion_amplitude=motion_amplitude,
            model_type=model_type,
            comfyui_running=self.comfy.is_running(),
        )

    def execute_scene_sequence(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Run a plan_scene_sequence storyboard sequentially."""
        steps = plan.get("steps") or []
        outputs: list[dict[str, Any]] = []
        hero_path = ""
        last_video = ""

        for step in steps:
            kind = step.get("kind")
            if kind == "t2i":
                r = self.generate_image(
                    prompt=step["prompt"],
                    style=step.get("style"),
                    content_rating="open",
                )
                saved = r.get("saved_files") or []
                if not saved:
                    raise RuntimeError(f"T2I beat {step.get('index')} produced no image")
                hero_path = saved[0]
                outputs.append({"beat": step.get("index"), "kind": "t2i", "result": r})
                continue

            if kind == "i2v":
                img = step.get("image_path") or hero_path
                if not img:
                    raise ValueError("I2V beat requires image_path or prior T2I output")
                r = self.generate_video(
                    prompt=step["prompt"],
                    mode="i2v",
                    style=step.get("style"),
                    negative_prompt=step.get("negative_prompt"),
                    workflow_id=step.get("workflow_id"),
                    image_path=img,
                    num_frames=step.get("num_frames"),
                    frame_rate=step.get("frame_rate"),
                    motion_amplitude=step.get("motion_amplitude") or 1.15,
                    smooth_motion=bool(step.get("smooth_motion")),
                    use_painter_i2v="painter" in (step.get("workflow_id") or ""),
                )
                saved = r.get("saved_files") or []
                if not saved:
                    raise RuntimeError(f"I2V beat {step.get('index')} produced no video")
                last_video = saved[-1]
                outputs.append({"beat": step.get("index"), "kind": "i2v", "result": r})
                continue

            if kind == "v2v":
                src = last_video
                if not src:
                    raise ValueError("V2V beat requires prior video output")
                r = self.generate_video(
                    prompt=step["prompt"],
                    mode="v2v",
                    style=step.get("style"),
                    negative_prompt=step.get("negative_prompt"),
                    workflow_id=step.get("workflow_id"),
                    video_path=src,
                    concat_source=bool(step.get("concat_source", True)),
                    num_frames=step.get("num_frames"),
                    frame_rate=step.get("frame_rate"),
                    motion_amplitude=step.get("motion_amplitude") or 1.15,
                    smooth_motion=bool(step.get("smooth_motion")),
                    use_painter_i2v="painter" in (step.get("workflow_id") or ""),
                )
                saved = r.get("saved_files") or []
                if not saved:
                    raise RuntimeError(f"V2V beat {step.get('index')} produced no video")
                last_video = saved[-1]
                outputs.append({"beat": step.get("index"), "kind": "v2v", "result": r})

        return {
            "executed": True,
            "beats": len(outputs),
            "final_video": last_video or None,
            "hero_image": hero_path or None,
            "outputs": outputs,
        }

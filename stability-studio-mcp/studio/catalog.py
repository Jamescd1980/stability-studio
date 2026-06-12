from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from studio.model_scanner import scan_checkpoints, scan_loras, scan_video_workflows, suggest_styles_from_models


def _deep_merge_family(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge family dict; override wins for scalars, lists extend/replace for known keys."""
    out = deepcopy(base)
    for key, val in override.items():
        if key == "extends":
            continue
        if key == "typical_defaults" and isinstance(val, dict):
            out.setdefault("typical_defaults", {}).update(val)
        elif key == "requires" and isinstance(val, list):
            out["requires"] = val
        elif key == "common_errors" and isinstance(val, list):
            out["common_errors"] = val
        else:
            out[key] = val
    return out


class StyleCatalog:
    def __init__(self, catalog_path: Path, cfg: dict[str, Any]) -> None:
        self.catalog_path = catalog_path
        self.cfg = cfg
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            return {"styles": {}, "video_workflows": {}}
        with self.catalog_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save(self) -> None:
        with self.catalog_path.open("w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @property
    def styles(self) -> dict[str, Any]:
        return self._data.get("styles", {})

    @property
    def video_workflows(self) -> dict[str, Any]:
        return self._data.get("video_workflows", {})

    @property
    def model_families(self) -> dict[str, Any]:
        return self._data.get("model_families", {})

    @property
    def art_food_groups(self) -> dict[str, Any]:
        return self._data.get("art_food_groups", {})

    def resolve_family(self, family_id: str) -> dict[str, Any]:
        """Return merged family metadata (handles extends)."""
        families = self.model_families
        raw = families.get(family_id, {})
        if not raw:
            return {"id": family_id, "label": family_id}
        if parent_id := raw.get("extends"):
            parent = self.resolve_family(parent_id)
            merged = _deep_merge_family(parent, raw)
        else:
            merged = deepcopy(raw)
        merged["id"] = family_id
        return merged

    def resolve_architecture(self, style_id: str) -> str:
        style = self.styles.get(style_id, {})
        if arch := style.get("architecture"):
            return str(arch)
        ckpt = (style.get("checkpoint") or "").lower()
        sid = style_id.lower()
        if "flux2_klein" in self.model_families and (
            "miracle" in ckpt or "klein" in ckpt or "flux" in ckpt
        ):
            return "flux2_klein"
        if "pony" in sid or "pony" in ckpt:
            return "pony_sdxl"
        if sid in {"anime", "ilustmix"} or "illustrious" in ckpt:
            return "sdxl_anime"
        if "cyberrealistic_final" in ckpt and "pony" not in ckpt:
            return "sd15"
        if "realisian" in ckpt or "abyssorangemix" in ckpt.replace("_", ""):
            return "sd15"
        if "mergedindreams" in ckpt.replace("_", ""):
            return "pony_sdxl"
        return "sdxl"

    def list_model_families(self) -> list[dict[str, Any]]:
        return [self.resolve_family(fid) for fid in self.model_families.keys()]

    def list_styles(self) -> list[dict[str, Any]]:
        out = []
        for key, style in self.styles.items():
            aliases = style.get("aliases", [])
            arch = self.resolve_architecture(key)
            family = self.resolve_family(arch)
            out.append(
                {
                    "id": key,
                    "description": style.get("description", ""),
                    "checkpoint": style.get("checkpoint"),
                    "architecture": arch,
                    "family_label": family.get("label", arch),
                    "workflow": family.get("workflow"),
                    "aliases": aliases,
                    "keywords": [key, *aliases],
                    "loras": style.get("loras", []),
                    "defaults": style.get("defaults", {}),
                    "prompt_style": family.get("prompt_style"),
                }
            )
        return out

    def _normalize_style_key(self, style_id: str) -> str:
        return style_id.lower().strip().replace(" ", "_").replace("-", "_")

    def _find_style_key(self, style_id: str) -> str:
        key = self._normalize_style_key(style_id)
        if key in self.styles:
            return key

        for sid, style in self.styles.items():
            aliases = [self._normalize_style_key(a) for a in style.get("aliases", [])]
            if key in aliases:
                return sid

        partial = [
            sid
            for sid in self.styles
            if key in sid or sid.startswith(key) or key.startswith(sid)
        ]
        if len(partial) == 1:
            return partial[0]

        available = ", ".join(self.styles.keys()) or "(none configured)"
        raise ValueError(f"Unknown style '{style_id}'. Available: {available}")

    def resolve_style(self, style_id: str | None) -> dict[str, Any]:
        if not style_id:
            style_id = self.cfg.get("default_style", "juggernaut")
        sid = self._find_style_key(style_id)
        return deepcopy(self.styles[sid])

    def resolve_generation_defaults(self, style_id: str | None) -> dict[str, Any]:
        """Merge model_family typical_defaults with per-style defaults (style wins)."""
        if not style_id:
            style_id = self.cfg.get("default_style", "juggernaut")
        sid = self._find_style_key(style_id)
        style = self.styles[sid]
        family = self.resolve_family(self.resolve_architecture(sid))
        merged = deepcopy(family.get("typical_defaults", {}))
        merged.update(style.get("defaults", {}))
        return merged

    def _normalize_workflow_ref(self, ref: str) -> str:
        return ref.strip().lower().replace("\\", "/")

    def _workflow_file_name(self, wf: dict[str, Any]) -> str:
        return Path(wf.get("file", "")).name.lower()

    def _find_video_workflow_key(self, workflow_id: str) -> str | None:
        workflows = self.video_workflows
        ref = self._normalize_workflow_ref(workflow_id)
        if ref in workflows:
            return ref

        file_matches: list[str] = []
        for key, wf in workflows.items():
            fname = self._workflow_file_name(wf)
            if not fname:
                continue
            if ref == fname or ref.endswith(fname) or fname in ref:
                file_matches.append(key)

        if len(file_matches) == 1:
            return file_matches[0]
        if len(file_matches) > 1:
            ref_slug = ref.replace(".json", "")
            for key in file_matches:
                wf_file = workflows[key].get("file", "").lower()
                if ref_slug and ref_slug in wf_file:
                    return key
            return file_matches[0]

        partial = [
            key
            for key in workflows
            if ref in key or key in ref or ref.replace("-", "_") in key.replace("-", "_")
        ]
        if len(partial) == 1:
            return partial[0]
        return None

    def list_video_workflow_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for key, wf in self.video_workflows.items():
            file_name = wf.get("file", "")
            if key.startswith("t2v"):
                mode = "t2v"
            elif key.startswith("v2v"):
                mode = "v2v"
            elif key.startswith("i2v"):
                mode = "i2v"
            else:
                mode = "unknown"
            entries.append(
                {
                    "id": key,
                    "mode": mode,
                    "description": wf.get("description", ""),
                    "file": file_name,
                }
            )
        return entries

    def resolve_video_workflow(self, workflow_id: str | None, mode: str) -> dict[str, Any]:
        workflows = self.video_workflows
        mode = (mode or "t2v").lower().strip()

        if workflow_id:
            key = self._find_video_workflow_key(workflow_id)
            if key:
                return deepcopy(workflows[key])
            available = ", ".join(
                f"{k} ({wf.get('file', '')})" for k, wf in workflows.items()
            )
            raise ValueError(
                f"Unknown video workflow '{workflow_id}'. "
                f"Use a catalog id (t2v, i2v_5b, v2v_5b, i2v, i2v_wan21, t2v_wan22) not the filename. "
                f"Available: {available}"
            )

        mode_matches = [
            (key, wf)
            for key, wf in workflows.items()
            if mode == "t2v" and key.startswith("t2v")
            or mode == "i2v" and key.startswith("i2v")
            or mode == "v2v" and key.startswith("v2v")
        ]
        if mode_matches:
            return deepcopy(mode_matches[0][1])

        raise ValueError(f"No {mode} workflow configured in catalog.yaml")

    def get_generation_context(self) -> dict[str, Any]:
        from studio.style_assets import check_all_style_assets

        sm = self.cfg.get("stability_matrix", {})
        models_dir = Path(sm.get("models", ""))
        workflows_dir = Path(sm.get("workflows", ""))

        checkpoints = scan_checkpoints(models_dir)
        loras = scan_loras(models_dir, self.cfg.get("extra_lora_paths"))
        video_files = scan_video_workflows(workflows_dir)
        text_encoders_dir = models_dir / "TextEncoders"
        text_encoders = (
            sorted(p.name for p in text_encoders_dir.glob("*.safetensors"))
            if text_encoders_dir.exists()
            else []
        )
        wan_umt5_ready = any("umt5" in n.lower() for n in text_encoders)

        catalog_map = {
            s["id"]: s["checkpoint"] for s in self.list_styles() if s.get("checkpoint")
        }
        style_readiness = check_all_style_assets(self.cfg, self)
        from studio.checkpoint_metadata import validate_style_architecture

        arch_checks: list[dict[str, Any]] = []
        for sid, style in self.styles.items():
            ckpt = style.get("checkpoint")
            if not ckpt or style.get("image_supported") is False:
                continue
            arch_checks.append(
                validate_style_architecture(
                    self.cfg,
                    sid,
                    self.resolve_architecture(sid),
                    ckpt,
                )
            )
        arch_mismatches = [c for c in arch_checks if c.get("mismatch")]

        families = {
            fid: {
                "label": self.resolve_family(fid).get("label"),
                "workflow": self.resolve_family(fid).get("workflow"),
                "typical_defaults": self.resolve_family(fid).get("typical_defaults"),
                "prompt_style": self.resolve_family(fid).get("prompt_style"),
                "vram_hint_gb": self.resolve_family(fid).get("vram_hint_gb"),
                "common_errors": self.resolve_family(fid).get("common_errors", []),
            }
            for fid in self.model_families.keys()
        }
        return {
            "model_families": families,
            "model_families_doc": "See MODEL-FAMILIES.md in repo root for full agent guide",
            "art_food_groups": self.art_food_groups or {},
            "art_food_groups_doc": "Pass food_group=anime|fantasy|cyberpunk|photoreal to edit_image. See IMAGE-EDITING.md.",
            "checkpoint_architecture_checks": arch_checks,
            "checkpoint_architecture_mismatches": arch_mismatches,
            "styles": self.list_styles(),
            "style_readiness": style_readiness,
            "style_to_checkpoint": catalog_map,
            "default_style": self.cfg.get("default_style", "juggernaut"),
            "checkpoints_installed": [c["file"] for c in checkpoints],
            "checkpoints": checkpoints,
            "loras": loras,
            "video_workflows": self.list_video_workflow_entries(),
            "video_workflow_ids": list(self.video_workflows.keys()),
            "video_workflow_files": video_files,
            "comfyui_url": self.cfg.get("comfyui", {}).get("url"),
            "invokeai_url": self.cfg.get("invokeai", {}).get("url"),
            "text_encoders": text_encoders,
            "wan_umt5_ready": wan_umt5_ready,
            "wan_umt5_download": (
                "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors"
                if not wan_umt5_ready
                else None
            ),
            "note": (
                "Call get_generation_context first. Check style_readiness.summary before generate_image. "
                "Image edits: setup_image_editing then edit_image (food_group: anime|fantasy|cyberpunk|photoreal). "
                "Flux2 styles: check_style_assets / download_style_assets. "
                "Wan video: check_wan_assets / download_wan_assets. "
                "Use style ids from styles[] (architecture field selects workflow builder)."
            ),
        }

    def refresh_scan_hints(self) -> dict[str, str]:
        sm = self.cfg.get("stability_matrix", {})
        models_dir = Path(sm.get("models", ""))
        checkpoints = scan_checkpoints(models_dir)
        return suggest_styles_from_models(checkpoints)

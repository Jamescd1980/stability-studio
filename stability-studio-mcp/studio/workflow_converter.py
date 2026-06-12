from __future__ import annotations

import re
from typing import Any

# UI workflow types remapped to installed ComfyUI API class names.
NODE_TYPE_ALIASES: dict[str, str] = {
    "Textbox": "PrimitiveStringMultiline",
}

SKIP_NODE_TYPES: frozenset[str] = frozenset(
    {
        "Label (rgthree)",
        "Note (rgthree)",
        "Note",
        "MarkdownNote",
        "Fast Groups Bypasser (rgthree)",
        "Reroute",
    }
)

PRIMITIVE_TYPES = frozenset({"INT", "FLOAT", "STRING", "BOOLEAN"})
SKIP_WIDGET_TOKENS = frozenset({"randomize", "fixed", "increment"})
GENERIC_FUZZY_TOKENS = frozenset(
    {
        "safetensors",
        "fp16",
        "fp8",
        "bf16",
        "fp32",
        "e4m3fn",
        "e5m2",
        "scaled",
        "enc",
        "model",
        "wan",
        "comfy",
        "pt",
        "pth",
        "fn",
    }
)
# When the workflow asks for this family, never fuzzy-match unrelated encoders (e.g. qwen via fp8).
_MODEL_FAMILY_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("umt5", ("umt5",)),
    ("t5xxl", ("umt5", "t5xxl")),
    ("wan2.1", ("wan2.1", "wan2")),
    ("wan2", ("wan2.1", "wan2")),
    ("wan21", ("wan2.1", "wan2")),
]
_INCOMPATIBLE_CHOICE_MARKERS = frozenset({"qwen", "clip", "hidream", "llama", "mistral"})


def is_api_workflow(workflow: dict[str, Any]) -> bool:
    if "nodes" in workflow:
        return False
    for value in workflow.values():
        if isinstance(value, dict) and "class_type" in value:
            return True
    return False


def _is_ui_only_node(node: dict[str, Any]) -> bool:
    node_type = node.get("type", "")
    if node_type in SKIP_NODE_TYPES:
        return True
    if "(rgthree)" in node_type and any(x in node_type for x in ("Label", "Note", "Bypasser")):
        return True
    if node.get("mode") in {2, 4}:
        return True
    return False


def _is_widget_spec(spec: Any) -> bool:
    if not isinstance(spec, list) or not spec:
        return False
    t = spec[0]
    if isinstance(t, list):
        return True
    return t in PRIMITIVE_TYPES


def _spec_type(spec: Any) -> str:
    if not isinstance(spec, list) or not spec:
        return ""
    t = spec[0]
    return "COMBO" if isinstance(t, list) else str(t)


def _widget_input_names(
    class_type: str,
    object_info: dict[str, Any],
    *,
    section: str | None = None,
) -> list[tuple[str, Any]]:
    if class_type not in object_info:
        return []
    names: list[tuple[str, Any]] = []
    info = object_info[class_type]["input"]
    sections = (section,) if section else ("required", "optional")
    for sec in sections:
        for name, spec in info.get(sec, {}).items():
            if _is_widget_spec(spec):
                names.append((name, spec))
    return names


def _combo_choices(spec: Any) -> list[Any]:
    if not isinstance(spec, list) or not spec:
        return []
    choices = spec[0]
    return choices if isinstance(choices, list) else []


def _combo_value_is_valid(spec: Any, value: Any) -> bool:
    choices = _combo_choices(spec)
    if not choices:
        return True
    return value in choices


def _combo_basename(value: Any) -> str:
    return str(value).replace("\\", "/").split("/")[-1].lower()


def _model_tokens(name: str) -> set[str]:
    tokens = set(re.split(r"[^a-z0-9]+", _combo_basename(name)))
    return {t for t in tokens if t and t not in GENERIC_FUZZY_TOKENS and not t.isdigit()}


def _choice_conflicts_with_request(raw: str, choice: str) -> bool:
    cl = _combo_basename(choice)
    if any(marker in cl for marker in _INCOMPATIBLE_CHOICE_MARKERS):
        if any(k in raw for k in ("umt5", "t5xxl", "t5", "wan2")):
            return True
    return False


def _wan_mode_tokens(name: str) -> set[str]:
    raw = _combo_basename(name)
    modes: set[str] = set()
    if "ti2v" in raw:
        modes.add("ti2v")
    if "t2v" in raw:
        modes.add("t2v")
    if "i2v" in raw:
        modes.add("i2v")
    if "vace" in raw:
        modes.add("vace")
    return modes


def _wan_size_tokens(name: str) -> set[str]:
    raw = _combo_basename(name)
    return {f"{m.group(1)}b" for m in re.finditer(r"(\d+(?:\.\d+)?)b", raw)}


def _wan_mode_compatible(requested: str, choice: str) -> bool:
    req_modes = _wan_mode_tokens(requested)
    if not req_modes:
        return True
    choice_modes = _wan_mode_tokens(choice)
    if "ti2v" in req_modes:
        return "ti2v" in choice_modes
    if "t2v" in req_modes and "i2v" not in req_modes:
        if "i2v" in choice_modes and "t2v" not in choice_modes and "ti2v" not in choice_modes:
            return False
    if "i2v" in req_modes and "t2v" not in req_modes:
        if "t2v" in choice_modes and "i2v" not in choice_modes and "ti2v" not in choice_modes:
            return False
    return True


def _score_wan_video_model_match(requested: str, choice: str) -> int:
    raw = _combo_basename(requested)
    cl = _combo_basename(choice)
    if _choice_conflicts_with_request(raw, cl):
        return -1
    if not _wan_mode_compatible(requested, choice):
        return -1

    score = len(_model_tokens(requested) & _model_tokens(choice))
    req_sizes = _wan_size_tokens(requested)
    choice_sizes = _wan_size_tokens(choice)
    if req_sizes and choice_sizes:
        if req_sizes & choice_sizes:
            score += 10
        else:
            score -= 5
    req_modes = _wan_mode_tokens(requested)
    choice_modes = _wan_mode_tokens(choice)
    if req_modes and req_modes & choice_modes:
        score += 10
    return score


def _pick_wan_video_model_value(spec: Any, value: Any) -> Any:
    choices = _combo_choices(spec)
    if not choices:
        return value
    if value in choices:
        return value

    best: Any | None = None
    best_score = -1
    for choice in choices:
        score = _score_wan_video_model_match(str(value), str(choice))
        if score > best_score:
            best_score = score
            best = choice
    if best is not None and best_score >= 0:
        return best

    wanted = _combo_basename(value)
    installed = ", ".join(str(c) for c in choices) or "(none)"
    raise ValueError(
        f"No compatible Wan video model for workflow request {wanted!r}. "
        f"Installed diffusion models: {installed}. "
        "T2V workflows need a Wan t2v checkpoint (e.g. wan2.1_t2v_1.3B); "
        "I2V workflows need an i2v checkpoint — they are not interchangeable."
    )


def _pick_combo_value(spec: Any, value: Any) -> Any:
    if not isinstance(spec, list) or not spec:
        return value
    choices = spec[0]
    if not isinstance(choices, list):
        return value
    if value in choices:
        return value

    raw = _combo_basename(value)
    for choice in choices:
        cl = _combo_basename(choice)
        if raw == cl:
            return choice
        if raw.endswith(cl) or cl.endswith(raw):
            if not _choice_conflicts_with_request(raw, cl):
                return choice

    for needle, patterns in _MODEL_FAMILY_PATTERNS:
        if needle not in raw:
            continue
        if any(p.startswith("wan") for p in patterns) or raw.startswith("wan"):
            picked = _pick_wan_video_model_value(spec, value)
            if picked is not None:
                return picked
            return None

        candidates: list[Any] = []
        for pattern in patterns:
            for choice in choices:
                cl = _combo_basename(choice)
                if pattern in cl and not _choice_conflicts_with_request(raw, cl):
                    candidates.append(choice)
        if not candidates:
            return None
        best = None
        best_score = 0
        for choice in candidates:
            score = len(_model_tokens(value) & _model_tokens(choice))
            if score > best_score:
                best_score = score
                best = choice
        if best is not None and best_score > 0:
            return best
        return None

    raw_tokens = _model_tokens(value)
    if not raw_tokens:
        return None
    best = None
    best_score = 0
    for choice in choices:
        if _choice_conflicts_with_request(raw, _combo_basename(choice)):
            continue
        score = len(raw_tokens & _model_tokens(choice))
        if score > best_score:
            best_score = score
            best = choice
    if best is not None and best_score > 0:
        return best
    return None


def _next_widget_value(name: str, spec: Any, values: list[Any]) -> Any | None:
    if not values:
        return None
    want = _spec_type(spec)
    idx = 0
    while idx < len(values):
        val = values[idx]
        if isinstance(val, (list, dict)):
            idx += 1
            continue
        if isinstance(val, str) and val in SKIP_WIDGET_TOKENS:
            idx += 1
            continue
        if want == "INT" and isinstance(val, str):
            idx += 1
            continue
        if want == "FLOAT" and isinstance(val, str) and val not in ("randomize",):
            idx += 1
            continue
        if want == "BOOLEAN" and not isinstance(val, bool):
            idx += 1
            continue
        if want == "COMBO" and isinstance(val, bool):
            idx += 1
            continue
        values.pop(idx)
        if want == "COMBO":
            picked = _pick_combo_value(spec, val)
            if not _combo_value_is_valid(spec, picked):
                continue
            return picked
        return val
    return None


def _build_setnode_sources(
    nodes: list[dict[str, Any]],
    link_by_id: dict[int, list[Any]],
) -> dict[str, tuple[int, int]]:
    sources: dict[str, tuple[int, int]] = {}
    for node in nodes:
        if node.get("type") != "SetNode":
            continue
        widgets = node.get("widgets_values") or []
        if not widgets:
            continue
        name = str(widgets[0])
        for inp in node.get("inputs", []):
            link_id = inp.get("link")
            if link_id is None:
                continue
            link = link_by_id.get(link_id)
            if not link:
                continue
            _, from_node, from_slot, _, _, _ = link[:6]
            sources[name] = (int(from_node), int(from_slot))
    return sources


def _resolve_link_source(
    node_id: int,
    slot: int,
    *,
    node_by_id: dict[int, dict[str, Any]],
    setnode_sources: dict[str, tuple[int, int]],
    depth: int = 0,
) -> tuple[int, int]:
    if depth > 32:
        return node_id, slot

    node = node_by_id.get(node_id)
    if node is None:
        return node_id, slot

    if node.get("type") == "GetNode":
        widgets = node.get("widgets_values") or []
        if widgets:
            key = str(widgets[0])
            if key in setnode_sources:
                upstream_id, upstream_slot = setnode_sources[key]
                return _resolve_link_source(
                    upstream_id,
                    upstream_slot,
                    node_by_id=node_by_id,
                    setnode_sources=setnode_sources,
                    depth=depth + 1,
                )

    return node_id, slot


def _apply_widgets(
    node: dict[str, Any],
    inputs: dict[str, Any],
    *,
    class_type: str,
    object_info: dict[str, Any] | None,
) -> None:
    widgets = node.get("widgets_values")
    if widgets is None:
        return

    if isinstance(widgets, dict):
        for key, val in widgets.items():
            if key in inputs or key in {"videopreview", "videopreview_over"}:
                continue
            inputs[key] = val
        return

    if not isinstance(widgets, list):
        return

    widget_inputs = [inp for inp in node.get("inputs", []) if inp.get("widget") is not None]
    if widget_inputs:
        widget_idx = 0
        for inp in widget_inputs:
            if widget_idx >= len(widgets):
                break
            if inp["name"] not in inputs:
                inputs[inp["name"]] = widgets[widget_idx]
            widget_idx += 1
            # KSampler / WanVideoSampler seed widgets store [value, "fixed"|"randomize"|...]
            if inp["name"] == "seed" and widget_idx < len(widgets):
                if isinstance(widgets[widget_idx], str) and widgets[widget_idx] in SKIP_WIDGET_TOKENS:
                    widget_idx += 1
        return

    if object_info and class_type in object_info:
        values = list(widgets)
        for name, spec in _widget_input_names(class_type, object_info, section="required"):
            if name in inputs:
                continue
            val = _next_widget_value(name, spec, values)
            if val is not None:
                inputs[name] = val
        for name, spec in _widget_input_names(class_type, object_info, section="optional"):
            if name in inputs:
                continue
            if not values:
                break
            val = _next_widget_value(name, spec, values)
            if val is None:
                break
            inputs[name] = val
        return

    # Legacy fallbacks when object_info unavailable.
    fallbacks: dict[str, list[str]] = {
        "WanVideoModelLoader": ["model", "base_precision", "quantization", "load_device", "attention_mode"],
        "LoadWanVideoT5TextEncoder": ["model_name", "precision", "load_device", "quantization"],
        "WanVideoVAELoader": ["model_name", "precision"],
        "WanVideoSampler": ["steps", "cfg", "shift", "seed", "force_offload", "scheduler", "riflex_freq_index"],
        "WanVideoContextOptions": [
            "context_schedule",
            "context_frames",
            "context_stride",
            "context_overlap",
            "freenoise",
            "verbose",
        ],
        "WanVideoEmptyEmbeds": ["width", "height", "num_frames"],
        "WanVideoEnhanceAVideo": ["weight", "start_percent", "end_percent"],
        "WanVideoDecode": ["enable_vae_tiling", "tile_x", "tile_y", "tile_stride_x", "tile_stride_y"],
        "WanVideoTeaCache": ["rel_l1_thresh", "start_step", "end_step", "cache_device", "use_coefficients", "mode"],
        "WanVideoTextEncode": ["positive_prompt", "negative_prompt", "force_offload"],
        "Wan22ImageToVideoLatent": ["width", "height", "length", "batch_size"],
        "UNETLoader": ["unet_name", "weight_dtype"],
        "CLIPLoader": ["clip_name", "type", "device"],
        "VAELoader": ["vae_name"],
        "VHS_VideoCombine": [
            "frame_rate",
            "loop_count",
            "filename_prefix",
            "format",
            "pix_fmt",
            "crf",
            "save_metadata",
            "trim_to_audio",
            "pingpong",
            "save_output",
        ],
    }
    names = fallbacks.get(class_type, [])
    for i, name in enumerate(names):
        if i < len(widgets) and name not in inputs:
            inputs[name] = widgets[i]


WAN_UMT5_DOWNLOAD = (
    "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors"
)


def _remap_wan_t5_encoder(api: dict[str, Any], object_info: dict[str, Any]) -> None:
    """Ensure LoadWanVideoT5TextEncoder uses umt5-xxl, not a wrong fuzzy match."""
    class_type = "LoadWanVideoT5TextEncoder"
    if class_type not in object_info:
        return

    spec = object_info[class_type]["input"]["required"]["model_name"]
    choices = _combo_choices(spec)
    if not choices:
        return

    umt5_choices = [c for c in choices if "umt5" in _combo_basename(c)]
    for node in api.values():
        if node.get("class_type") != class_type:
            continue
        inputs = node.get("inputs", {})
        current = inputs.get("model_name")
        if current in choices and "umt5" in _combo_basename(str(current)):
            continue
        if umt5_choices:
            inputs["model_name"] = umt5_choices[0]
            continue
        installed = ", ".join(str(c) for c in choices) or "(none)"
        wanted = _combo_basename(current) if current else "umt5-xxl-enc-bf16.safetensors"
        raise ValueError(
            "Wan video requires the umt5-xxl text encoder "
            f"(workflow wanted {wanted!r}). "
            f"Installed in TextEncoders: {installed}. "
            "SDXL t5xxl_fp16 is not compatible with Wan. "
            "Download umt5-xxl-enc-bf16.safetensors to "
            "Stability Matrix / Models / TextEncoders. "
            f"URL: {WAN_UMT5_DOWNLOAD}"
        )


def _remap_wan_video_model(
    api: dict[str, Any],
    object_info: dict[str, Any],
    *,
    wan_wanted: dict[str, Any],
) -> None:
    """Re-validate WanVideoModelLoader picks against the workflow's original request."""
    class_type = "WanVideoModelLoader"
    if class_type not in object_info or not wan_wanted:
        return

    spec = object_info[class_type]["input"]["required"]["model"]
    for nid, wanted in wan_wanted.items():
        node = api.get(nid)
        if not node or node.get("class_type") != class_type:
            continue
        inputs = node.get("inputs", {})
        current = inputs.get("model")
        if current is not None and _wan_mode_compatible(str(wanted), str(current)):
            continue
        inputs["model"] = _pick_wan_video_model_value(spec, wanted)


def remap_api_inputs_to_installed(api: dict[str, Any], object_info: dict[str, Any]) -> None:
    """Snap combo/widget values to lists ComfyUI reports as installed."""
    wan_wanted: dict[str, Any] = {}
    for nid, node in api.items():
        class_type = node.get("class_type", "")
        if class_type not in object_info:
            continue
        specs = dict(_widget_input_names(class_type, object_info))
        inputs = node.get("inputs", {})
        for name, spec in specs.items():
            if name not in inputs:
                continue
            if _spec_type(spec) != "COMBO":
                continue
            original = inputs[name]
            if class_type in {"WanVideoModelLoader", "UNETLoader"} and name in {"model", "unet_name"}:
                if class_type == "WanVideoModelLoader":
                    wan_wanted[nid] = original
                picked = _pick_wan_video_model_value(spec, original)
            else:
                picked = _pick_combo_value(spec, original)
            if picked is not None and _combo_value_is_valid(spec, picked):
                inputs[name] = picked
            else:
                del inputs[name]

    _remap_wan_t5_encoder(api, object_info)
    _remap_wan_video_model(api, object_info, wan_wanted=wan_wanted)
    _remap_wan_clip_loader(api, object_info)
    _remap_wan_vae_loader(api, object_info)
    _remap_wan_attention_mode(api, object_info)


def _pick_wan22_vae_name(choices: list[str]) -> str | None:
    """Prefer Wan 2.2 VAE for native TI2V graphs; avoid Wan 2.1 fallbacks."""
    wan22 = [c for c in choices if "wan2.2" in _combo_basename(c).lower() or "wan_2.2" in _combo_basename(c).lower()]
    if wan22:
        return wan22[0]
    wan = [c for c in choices if "wan" in _combo_basename(c).lower() and "2.1" not in _combo_basename(c).lower()]
    return wan[0] if wan else None


def _remap_wan_vae_loader(api: dict[str, Any], object_info: dict[str, Any]) -> None:
    """Ensure native Wan 2.2 workflows decode with wan2.2_vae, not legacy Wan 2.1 VAE."""
    class_type = "VAELoader"
    if class_type not in object_info:
        return
    spec = object_info[class_type]["input"]["required"].get("vae_name")
    choices = _combo_choices(spec)
    if not choices:
        return
    picked = _pick_wan22_vae_name(choices)
    if not picked:
        return
    for node in api.values():
        if node.get("class_type") != class_type:
            continue
        current = str(node.get("inputs", {}).get("vae_name", ""))
        current_base = _combo_basename(current).lower()
        if current in choices and ("wan2.2" in current_base or "wan_2.2" in current_base):
            continue
        node.setdefault("inputs", {})["vae_name"] = picked


def _pick_wan_native_clip_name(choices: list[str]) -> str | None:
    """Native CLIPLoader (type=wan) needs full CLIP weights, not encoder-only exports."""
    umt5_choices = [c for c in choices if "umt5" in _combo_basename(c).lower()]
    if not umt5_choices:
        return None
    full = [c for c in umt5_choices if "-enc-" not in _combo_basename(c).lower()]
    prefer = [c for c in full if "fp8" in _combo_basename(c).lower()] or full
    return (prefer or umt5_choices)[0]


def _remap_wan_clip_loader(api: dict[str, Any], object_info: dict[str, Any]) -> None:
    """Use an installed umt5 text encoder for native Wan 2.2 CLIPLoader nodes."""
    class_type = "CLIPLoader"
    if class_type not in object_info:
        return
    spec = object_info[class_type]["input"]["required"].get("clip_name")
    choices = _combo_choices(spec)
    if not choices:
        return
    picked = _pick_wan_native_clip_name(choices)
    if not picked:
        return
    for node in api.values():
        if node.get("class_type") != class_type:
            continue
        inputs = node.get("inputs", {})
        if inputs.get("type") not in {"wan", None} and str(inputs.get("type", "")).lower() != "wan":
            continue
        current = str(inputs.get("clip_name", ""))
        current_base = _combo_basename(current).lower()
        if (
            current in choices
            and "umt5" in current_base
            and "-enc-" not in current_base
        ):
            continue
        inputs["clip_name"] = picked


def _remap_wan_attention_mode(api: dict[str, Any], object_info: dict[str, Any]) -> None:
    """Use sdpa when workflows request sageattn but SageAttention is not installed."""
    class_type = "WanVideoModelLoader"
    if class_type not in object_info:
        return
    info = object_info[class_type]["input"]
    spec = info.get("required", {}).get("attention_mode") or info.get("optional", {}).get("attention_mode")
    choices = _combo_choices(spec) if spec else []
    fallback = "sdpa" if "sdpa" in choices else (choices[0] if choices else "sdpa")
    for node in api.values():
        if node.get("class_type") != class_type:
            continue
        mode = node.get("inputs", {}).get("attention_mode")
        if mode == "sageattn":
            node["inputs"]["attention_mode"] = fallback


def wire_implicit_wan_vae_links(api: dict[str, Any]) -> None:
    """Wire VAE into Wan nodes when the UI graph used Anything Everywhere instead of links."""
    vae_loaders = [nid for nid, node in api.items() if node.get("class_type") == "WanVideoVAELoader"]
    if not vae_loaders:
        return
    vae_src = vae_loaders[0]
    needs_vae = {
        "WanVideoImageToVideoEncode",
        "WanVideoDecode",
        "WanVideoContextOptions",
        "WanVideoEncodeLatentBatch",
    }
    for node in api.values():
        if node.get("class_type") not in needs_vae:
            continue
        inputs = node.setdefault("inputs", {})
        if not inputs.get("vae"):
            inputs["vae"] = [vae_src, 0]


def ui_to_api(
    workflow: dict[str, Any],
    object_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert ComfyUI UI-format workflow to API prompt dict."""
    if is_api_workflow(workflow):
        return workflow

    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    node_by_id: dict[int, dict[str, Any]] = {node["id"]: node for node in nodes}
    link_by_id: dict[int, list[Any]] = {link[0]: link for link in links if link}
    setnode_sources = _build_setnode_sources(nodes, link_by_id)

    api: dict[str, Any] = {}
    for node in nodes:
        if _is_ui_only_node(node):
            continue
        if node.get("type") in {"GetNode", "SetNode"}:
            continue

        nid = str(node["id"])
        class_type = NODE_TYPE_ALIASES.get(node["type"], node["type"])
        api[nid] = {"class_type": class_type, "inputs": {}}

    for node in nodes:
        nid = str(node["id"])
        if nid not in api:
            continue

        class_type = api[nid]["class_type"]
        inputs = api[nid]["inputs"]

        for inp in node.get("inputs", []):
            link_id = inp.get("link")
            if link_id is None:
                continue
            link = link_by_id.get(link_id)
            if not link:
                continue
            _, from_node, from_slot, _, _, _ = link[:6]
            resolved_id, resolved_slot = _resolve_link_source(
                int(from_node),
                int(from_slot),
                node_by_id=node_by_id,
                setnode_sources=setnode_sources,
            )
            if str(resolved_id) not in api:
                continue
            inputs[inp["name"]] = [str(resolved_id), resolved_slot]

        if node.get("type") == "Textbox":
            widgets = node.get("widgets_values") or []
            if widgets and "value" not in inputs:
                inputs["value"] = widgets[0]

        _apply_widgets(node, inputs, class_type=class_type, object_info=object_info)

    if object_info:
        remap_api_inputs_to_installed(api, object_info)

    wire_implicit_wan_vae_links(api)

    return api

from __future__ import annotations

import random
from typing import Any


def build_txt2img_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 28,
    cfg: float = 7.0,
    sampler: str = "dpmpp_2m",
    scheduler: str = "karras",
    loras: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a ComfyUI API-format SDXL/SD1.5 txt2img workflow."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    model_src = ["4", 0]
    clip_src = ["4", 1]
    last_model_node = "4"
    last_clip_node = "4"

    workflow: dict[str, Any] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
    }

    for i, lora in enumerate(loras):
        node_id = str(10 + i)
        workflow[node_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": [last_model_node, 0],
                "clip": [last_clip_node, 1],
            },
        }
        last_model_node = node_id
        last_clip_node = node_id

    model_src = [last_model_node, 0]
    clip_src = [last_clip_node, 1]

    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": clip_src},
    }
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": clip_src},
    }
    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": model_src,
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
    }

    return workflow


def build_i2i_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    image_filename: str,
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 28,
    cfg: float = 7.0,
    sampler: str = "euler_ancestral",
    scheduler: str = "normal",
    denoising_strength: float = 0.45,
    loras: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a ComfyUI API-format SDXL I2I (img2img) workflow with optional LoRAs."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    last_model_node = "4"
    last_clip_node = "4"

    workflow: dict[str, Any] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename},
        },
        "12": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["10", 0],
                "upscale_method": "lanczos",
                "width": width,
                "height": height,
                "crop": "center",
            },
        },
        "11": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["12", 0], "vae": ["4", 2]},
        },
    }

    for i, lora in enumerate(loras):
        node_id = str(20 + i)
        workflow[node_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": [last_model_node, 0],
                "clip": [last_clip_node, 1],
            },
        }
        last_model_node = node_id
        last_clip_node = node_id

    model_src = [last_model_node, 0]
    clip_src = [last_clip_node, 1]

    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": clip_src},
    }
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": clip_src},
    }
    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": float(denoising_strength),
            "model": model_src,
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["11", 0],
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
    }

    return workflow


def build_inpaint_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    image_filename: str,
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 25,
    cfg: float = 5.0,
    denoising_strength: float = 0.35,
    loras: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a ComfyUI API-format inpainting workflow (full-image latent edit)."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    last_model_node = "4"
    last_clip_node = "4"

    workflow: dict[str, Any] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename},
        },
        "11": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["10", 0], "vae": ["4", 2]},
        },
    }

    for i, lora in enumerate(loras):
        node_id = str(20 + i)
        workflow[node_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": [last_model_node, 0],
                "clip": [last_clip_node, 1],
            },
        }
        last_model_node = node_id
        last_clip_node = node_id

    model_src = [last_model_node, 0]
    clip_src = [last_clip_node, 1]

    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": clip_src},
    }
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": clip_src},
    }
    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": float(denoising_strength),
            "model": model_src,
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["11", 0],
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
    }

    return workflow


def inject_prompts_ui_workflow(
    workflow: dict[str, Any],
    *,
    positive: str,
    negative: str,
    prompt_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Inject prompts into a ComfyUI UI-format workflow JSON."""
    import copy

    wf = copy.deepcopy(workflow)
    if "nodes" not in wf:
        return wf

    configured = prompt_nodes or []
    configured_types = {n.get("type") for n in configured}
    aux_textboxes = _textbox_ids_for_textcombiner_aux(wf)

    for node in wf.get("nodes", []):
        node_type = node.get("type", "")
        widgets = node.get("widgets_values")
        if widgets is None:
            continue

        match = next((p for p in configured if p.get("type") == node_type), None)

        if node_type in {"CLIPTextEncode", "CLIPTextEncodeSDXL"}:
            title = str(node.get("title") or "").lower()
            if isinstance(widgets, list) and widgets:
                if "negative" in title:
                    widgets[0] = negative
                elif match:
                    pos_i = match.get("positive_index", 0)
                    if pos_i < len(widgets):
                        widgets[pos_i] = positive
                else:
                    widgets[0] = positive

        elif node_type == "WanVideoTextEncode":
            pos_i = (match or {}).get("positive_index", 0)
            neg_i = (match or {}).get("negative_index", 1)
            if isinstance(widgets, list):
                if pos_i < len(widgets):
                    widgets[pos_i] = positive
                if neg_i < len(widgets):
                    widgets[neg_i] = negative

        elif node_type == "TextCombinerTwo":
            if isinstance(widgets, list) and widgets:
                widgets[0] = positive

        elif node_type == "Textbox":
            if node["id"] in aux_textboxes and isinstance(widgets, list) and widgets:
                widgets[0] = ""

        elif node_type in configured_types and match:
            pos_i = match.get("positive_index", 0)
            if isinstance(widgets, list) and pos_i < len(widgets):
                widgets[pos_i] = positive

    return wf


def _textbox_ids_for_textcombiner_aux(wf: dict[str, Any]) -> set[int]:
    """Textbox nodes wired to TextCombinerTwo.text2 carry baked workflow defaults — clear them."""
    nodes_by_id = {n["id"]: n for n in wf.get("nodes", [])}
    link_by_id = {link[0]: link for link in wf.get("links", []) if link}
    aux: set[int] = set()
    for node in wf.get("nodes", []):
        if node.get("type") != "TextCombinerTwo":
            continue
        for inp in node.get("inputs", []):
            if inp.get("name") != "text2":
                continue
            link = link_by_id.get(inp.get("link"))
            if not link:
                continue
            src = nodes_by_id.get(link[1])
            if src and src.get("type") == "Textbox":
                aux.add(src["id"])
    return aux


def inject_i2v_ui_workflow(
    workflow: dict[str, Any],
    *,
    image_filename: str,
    num_frames: int | None = None,
    frame_rate: float | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Set LoadImage source and optional encode size / frames / fps on a UI-format I2V workflow."""
    import copy

    wf = copy.deepcopy(workflow)
    if "nodes" not in wf:
        return wf

    nodes_by_id = {n["id"]: n for n in wf.get("nodes", [])}
    frame_seconds: int | None = None
    if num_frames is not None and frame_rate and frame_rate > 0:
        frame_seconds = max(1, int(round((num_frames - 1) / frame_rate)))

    for node in wf.get("nodes", []):
        node_type = node.get("type", "")
        widgets = node.get("widgets_values")
        if node_type == "LoadImage" and isinstance(widgets, list) and widgets:
            widgets[0] = image_filename
        elif node_type in {
            "WanVideoImageToVideoEncode",
            "WanVaceToVideo",
            "WanVideoEmptyEmbeds",
            "Wan22ImageToVideoLatent",
            "PainterI2V",
        }:
            if isinstance(widgets, list) and len(widgets) > 2:
                if width is not None:
                    widgets[0] = width
                if height is not None:
                    widgets[1] = height
                if num_frames is not None:
                    widgets[2] = num_frames
        elif frame_seconds is not None and node_type == "easy int" and isinstance(widgets, list):
            # Wan 2.2 I2V: seconds node -> SimpleMath+ `a*16+1` -> num_frames
            node_id = node["id"]
            for link in wf.get("links", []):
                if link[1] != node_id:
                    continue
                target = nodes_by_id.get(link[3])
                if not target:
                    continue
                tw = target.get("widgets_values")
                if target.get("type") == "SimpleMath+" and isinstance(tw, list) and tw and tw[0] == "a*16+1":
                    widgets[0] = frame_seconds
                    break
        if frame_rate is not None and node_type == "VHS_VideoCombine":
            if isinstance(widgets, dict):
                widgets["frame_rate"] = frame_rate
            elif isinstance(widgets, list):
                widgets[0] = frame_rate

    return wf


def inject_i2v_native_quality(
    workflow: dict[str, Any],
    *,
    vae_name: str = "wan2.2_vae.safetensors",
    steps: int = 40,
    cfg: float = 5.5,
    crf: int = 17,
) -> dict[str, Any]:
    """Tune native Wan 2.2 I2V graph: matched VAE, sampler steps, and encode quality."""
    import copy

    wf = copy.deepcopy(workflow)
    if "nodes" not in wf:
        return wf

    for node in wf.get("nodes", []):
        node_type = node.get("type", "")
        widgets = node.get("widgets_values")
        if node_type == "VAELoader" and isinstance(widgets, list) and widgets:
            widgets[0] = vae_name
        elif node_type == "KSampler" and isinstance(widgets, list) and len(widgets) >= 7:
            widgets[2] = steps
            widgets[3] = cfg
        elif node_type == "VHS_VideoCombine" and isinstance(widgets, dict):
            widgets["crf"] = crf

    return wf


def _max_node_and_link_ids(wf: dict[str, Any]) -> tuple[int, int]:
    max_node = max((int(n["id"]) for n in wf.get("nodes", [])), default=0)
    max_link = max((int(link[0]) for link in wf.get("links", []) if link), default=0)
    return max_node, max_link


def _find_link(wf: dict[str, Any], *, src: int | None = None, dst: int | None = None) -> dict[str, Any] | None:
    for link in wf.get("links", []):
        if not link:
            continue
        if src is not None and link[1] != src:
            continue
        if dst is not None and link[3] != dst:
            continue
        return {
            "id": link[0],
            "src": link[1],
            "src_slot": link[2],
            "dst": link[3],
            "dst_slot": link[4],
            "type": link[5],
        }
    return None


def _set_node_input_link(wf: dict[str, Any], node_id: int, input_name: str, link_id: int | None) -> None:
    nodes_by_id = {n["id"]: n for n in wf.get("nodes", [])}
    node = nodes_by_id.get(node_id)
    if not node:
        return
    for inp in node.get("inputs", []):
        if inp.get("name") == input_name:
            inp["link"] = link_id
            return


def inject_wan_unet_loras_ui_workflow(
    workflow: dict[str, Any],
    loras: list[dict[str, Any]],
) -> dict[str, Any]:
    """Chain LoraLoaderModelOnly nodes after UNETLoader for native Wan 2.2 I2V."""
    import copy

    if not loras:
        return workflow

    wf = copy.deepcopy(workflow)
    if "nodes" not in wf:
        return wf

    unet = next((n for n in wf["nodes"] if n.get("type") == "UNETLoader"), None)
    ms = next((n for n in wf["nodes"] if n.get("type") == "ModelSamplingSD3"), None)
    if not unet or not ms:
        return wf

    bridge = _find_link(wf, src=unet["id"], dst=ms["id"])
    if not bridge:
        return wf

    max_node, max_link = _max_node_and_link_ids(wf)
    prev_src_node = unet["id"]
    prev_src_slot = 0

    for lora in loras:
        max_node += 1
        max_link += 1
        lora_node_id = max_node
        in_link_id = max_link

        lora_name = lora.get("file") or lora.get("name")
        strength = float(lora.get("weight", 0.6))
        wf["nodes"].append(
            {
                "id": lora_node_id,
                "type": "LoraLoaderModelOnly",
                "pos": [200, 60],
                "size": [320, 82],
                "flags": {},
                "order": 5,
                "mode": 0,
                "inputs": [
                    {"name": "model", "type": "MODEL", "link": in_link_id},
                ],
                "outputs": [
                    {"name": "MODEL", "type": "MODEL", "slot_index": 0, "links": []},
                ],
                "properties": {"Node name for S&R": "LoraLoaderModelOnly"},
                "widgets_values": [lora_name, strength],
            }
        )
        wf["links"].append([in_link_id, prev_src_node, prev_src_slot, lora_node_id, 0, "MODEL"])
        _set_node_input_link(wf, lora_node_id, "model", in_link_id)
        prev_src_node = lora_node_id
        prev_src_slot = 0

    # Rewire UNET -> ModelSamplingSD3 to UNET -> ... -> last LoRA -> ModelSamplingSD3
    for link in wf["links"]:
        if link[0] == bridge["id"]:
            link[1] = prev_src_node
            link[2] = prev_src_slot
            break
    _set_node_input_link(wf, ms["id"], "model", bridge["id"])

    return wf


def inject_painter_i2v_ui_workflow(
    workflow: dict[str, Any],
    *,
    motion_amplitude: float = 1.15,
    width: int | None = None,
    height: int | None = None,
    num_frames: int | None = None,
) -> dict[str, Any]:
    """
    Replace Wan22ImageToVideoLatent with PainterI2V (motion_amplitude control).
    Requires ComfyUI-PainterI2V custom node.
    """
    import copy

    wf = copy.deepcopy(workflow)
    if "nodes" not in wf:
        return wf

    wan_node = next((n for n in wf["nodes"] if n.get("type") == "Wan22ImageToVideoLatent"), None)
    ksampler = next((n for n in wf["nodes"] if n.get("type") == "KSampler"), None)
    if not wan_node or not ksampler:
        return wf

    pos_node = next(
        (
            n
            for n in wf["nodes"]
            if n.get("type") == "CLIPTextEncode"
            and "negative" not in str(n.get("title", "")).lower()
        ),
        None,
    )
    neg_node = next(
        (
            n
            for n in wf["nodes"]
            if n.get("type") == "CLIPTextEncode"
            and "negative" in str(n.get("title", "")).lower()
        ),
        None,
    )
    if not pos_node or not neg_node:
        return wf

    widgets = wan_node.get("widgets_values") or [480, 832, 65, 1]
    vid_w = width if width is not None else int(widgets[0])
    vid_h = height if height is not None else int(widgets[1])
    vid_len = num_frames if num_frames is not None else int(widgets[2])
    batch = int(widgets[3]) if len(widgets) > 3 else 1

    max_node, max_link = _max_node_and_link_ids(wf)
    painter_id = max_node + 1

    link_pos_in = max_link + 1
    link_neg_in = max_link + 2
    link_vae_in = max_link + 3
    link_img_in = max_link + 4
    link_pos_out = max_link + 5
    link_neg_out = max_link + 6
    link_lat_out = max_link + 7

    vae_link = _find_link(wf, dst=wan_node["id"])
    img_link = None
    for link in wf.get("links", []):
        if link and link[3] == wan_node["id"] and link[4] == 1:
            img_link = link
            break

    wf["nodes"] = [n for n in wf["nodes"] if n["id"] != wan_node["id"]]
    wf["links"] = [
        link
        for link in wf.get("links", [])
        if link
        and not (
            link[3] == wan_node["id"]
            or (link[1] == wan_node["id"])
            or (link[1] == pos_node["id"] and link[3] == ksampler["id"] and link[4] == 1)
            or (link[1] == neg_node["id"] and link[3] == ksampler["id"] and link[4] == 2)
        )
    ]

    wf["nodes"].append(
        {
            "id": painter_id,
            "type": "PainterI2V",
            "pos": wan_node.get("pos", [420, 610]),
            "size": [300, 280],
            "flags": {},
            "order": wan_node.get("order", 8),
            "mode": 0,
            "inputs": [
                {"name": "positive", "type": "CONDITIONING", "link": link_pos_in},
                {"name": "negative", "type": "CONDITIONING", "link": link_neg_in},
                {"name": "vae", "type": "VAE", "link": link_vae_in},
                {"name": "start_image", "type": "IMAGE", "link": link_img_in},
            ],
            "outputs": [
                {"name": "positive", "type": "CONDITIONING", "slot_index": 0, "links": [link_pos_out]},
                {"name": "negative", "type": "CONDITIONING", "slot_index": 0, "links": [link_neg_out]},
                {"name": "latent", "type": "LATENT", "slot_index": 0, "links": [link_lat_out]},
            ],
            "properties": {"Node name for S&R": "PainterI2V"},
            "widgets_values": [vid_w, vid_h, vid_len, batch, float(motion_amplitude)],
        }
    )

    vae_src = vae_link["src"] if vae_link else None
    img_src = img_link[1] if img_link else None

    wf["links"].extend(
        [
            [link_pos_in, pos_node["id"], 0, painter_id, 0, "CONDITIONING"],
            [link_neg_in, neg_node["id"], 0, painter_id, 1, "CONDITIONING"],
            [link_pos_out, painter_id, 0, ksampler["id"], 1, "CONDITIONING"],
            [link_neg_out, painter_id, 1, ksampler["id"], 2, "CONDITIONING"],
            [link_lat_out, painter_id, 2, ksampler["id"], 3, "LATENT"],
        ]
    )
    if vae_src is not None:
        wf["links"].append([link_vae_in, vae_src, 0, painter_id, 2, "VAE"])
        _set_node_input_link(wf, painter_id, "vae", link_vae_in)
    if img_src is not None:
        wf["links"].append([link_img_in, img_src, 0, painter_id, 3, "IMAGE"])
        _set_node_input_link(wf, painter_id, "start_image", link_img_in)

    _set_node_input_link(wf, painter_id, "positive", link_pos_in)
    _set_node_input_link(wf, painter_id, "negative", link_neg_in)
    _set_node_input_link(wf, ksampler["id"], "positive", link_pos_out)
    _set_node_input_link(wf, ksampler["id"], "negative", link_neg_out)
    _set_node_input_link(wf, ksampler["id"], "latent_image", link_lat_out)

    return wf


def inject_i2v_enhancements_ui_workflow(
    workflow: dict[str, Any],
    *,
    loras: list[dict[str, Any]] | None = None,
    use_painter_i2v: bool = False,
    motion_amplitude: float = 1.15,
    width: int | None = None,
    height: int | None = None,
    num_frames: int | None = None,
) -> dict[str, Any]:
    wf = workflow
    if loras:
        wf = inject_wan_unet_loras_ui_workflow(wf, loras)
    if use_painter_i2v:
        wf = inject_painter_i2v_ui_workflow(
            wf,
            motion_amplitude=motion_amplitude,
            width=width,
            height=height,
            num_frames=num_frames,
        )
    return wf


def build_wan21_i2v_ui_workflow(
    t2v_ui_workflow: dict[str, Any],
    *,
    image_filename: str,
    limits: dict[str, Any],
    num_frames: int,
    frame_rate: float,
    gpu_only: bool = True,
) -> dict[str, Any]:
    """
    Convert the validated Wan 2.1 T2V UI workflow into a GPU-friendly I2V graph.

    Uses wan2.1_i2v_480p_14B with fp8 on main_device — no CPU offload when gpu_only.
    """
    import copy

    caps = limits.get("video_i2v", {})
    width = int(caps.get("max_width", 480))
    height = int(caps.get("max_height", 640))
    quantization = str(caps.get("quantization", "fp8_e4m3fn"))
    load_device = str(caps.get("load_device", "main_device"))
    t5_load_device = str(caps.get("t5_load_device", "offload_device"))
    force_offload = bool(caps.get("force_offload", False))
    context_frames = min(num_frames, 49)

    wf = copy.deepcopy(t2v_ui_workflow)
    if "nodes" not in wf:
        raise ValueError("Expected ComfyUI UI-format workflow with nodes[]")

    empty_id = next(n["id"] for n in wf["nodes"] if n.get("type") == "WanVideoEmptyEmbeds")
    sampler_id = next(n["id"] for n in wf["nodes"] if n.get("type") == "WanVideoSampler")
    vae_id = next(n["id"] for n in wf["nodes"] if n.get("type") == "WanVideoVAELoader")

    for node in wf["nodes"]:
        node_type = node.get("type", "")
        widgets = node.get("widgets_values")
        if node_type == "WanVideoModelLoader" and isinstance(widgets, list):
            widgets[:] = [
                "wan2.1_i2v_480p_14B_bf16.safetensors",
                "bf16",
                quantization,
                load_device,
                "sdpa",
            ]
        elif node_type == "LoadWanVideoT5TextEncoder" and isinstance(widgets, list):
            widgets[0] = "umt5-xxl-enc-bf16.safetensors"
            widgets[1] = "bf16"
            widgets[2] = t5_load_device
            widgets[3] = "disabled"
        elif node_type == "WanVideoTextEncode" and isinstance(widgets, list) and len(widgets) > 2:
            widgets[2] = True  # force_offload T5 after encode to free VRAM for 14B I2V
        elif node_type == "WanVideoContextOptions" and isinstance(widgets, list) and len(widgets) > 3:
            widgets[1] = context_frames
        elif node_type == "WanVideoSampler" and isinstance(widgets, list) and len(widgets) > 5:
            widgets[0] = 20
            widgets[1] = 5.0
            widgets[5] = force_offload
        elif node_type == "WanVideoTeaCache" and isinstance(widgets, list) and len(widgets) > 3:
            widgets[3] = "offload_device" if force_offload else load_device
        elif node_type == "VHS_VideoCombine" and isinstance(widgets, dict):
            widgets["frame_rate"] = frame_rate

    max_link = max(lk[0] for lk in wf["links"])
    load_id, enc_id = 100, 101
    load_node = {
        "id": load_id,
        "type": "LoadImage",
        "pos": [0, 0],
        "size": [315, 314],
        "flags": {},
        "order": 0,
        "mode": 0,
        "inputs": [],
        "outputs": [{"name": "IMAGE", "type": "IMAGE", "slot_index": 0, "links": [max_link + 1]}],
        "properties": {"Node name for S&R": "LoadImage"},
        "widgets_values": [image_filename, "image"],
    }
    enc_node = {
        "id": enc_id,
        "type": "WanVideoImageToVideoEncode",
        "pos": [0, 0],
        "size": [315, 200],
        "flags": {},
        "order": 0,
        "mode": 0,
        "inputs": [
            {"name": "vae", "type": "WANVAE", "link": max_link + 2},
            {"name": "start_image", "type": "IMAGE", "link": max_link + 1},
        ],
        "outputs": [
            {"name": "image_embeds", "type": "WANVIDIMAGE_EMBEDS", "slot_index": 0, "links": [max_link + 3]}
        ],
        "properties": {"Node name for S&R": "WanVideoImageToVideoEncode"},
        "widgets_values": [width, height, num_frames, 0, 1, 1, force_offload, True, False],
    }

    wf["nodes"] = [n for n in wf["nodes"] if n.get("type") != "WanVideoEmptyEmbeds"] + [load_node, enc_node]
    wf["links"] = [lk for lk in wf["links"] if lk[1] != empty_id and lk[3] != empty_id]
    wf["links"] += [
        [max_link + 1, load_id, 0, enc_id, 1, "IMAGE"],
        [max_link + 2, vae_id, 0, enc_id, 0, "WANVAE"],
        [max_link + 3, enc_id, 0, sampler_id, 2, "WANVIDIMAGE_EMBEDS"],
    ]
    for node in wf["nodes"]:
        if node["id"] == sampler_id:
            for inp in node.get("inputs", []):
                if inp.get("name") == "image_embeds":
                    inp["link"] = max_link + 3

    return wf


_FLUX_CHECKPOINT_MARKERS = ("flux", "miraclein", "klein")


def is_flux_checkpoint(checkpoint: str) -> bool:
    """True when checkpoint needs Flux2 Klein pipeline (not SDXL CheckpointLoaderSimple)."""
    name = checkpoint.lower()
    return any(m in name for m in _FLUX_CHECKPOINT_MARKERS)


def build_flux2_klein_txt2img_workflow(
    *,
    unet: str,
    clip: str,
    vae: str,
    positive: str,
    negative: str = "",
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 20,
    cfg: float = 3.5,
    sampler: str = "euler",
    save_prefix: str = "studio_agent",
) -> dict[str, Any]:
    """Native ComfyUI Flux.2 Klein txt2img (UNETLoader + CLIPLoader + Flux2Scheduler)."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    return {
        "10": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet, "weight_dtype": "default"},
        },
        "11": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": clip, "type": "flux2", "device": "default"},
        },
        "12": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae},
        },
        "13": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["11", 0]},
        },
        "14": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["11", 0]},
        },
        "15": {
            "class_type": "EmptyFlux2LatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "16": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": seed},
        },
        "17": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": sampler},
        },
        "18": {
            "class_type": "Flux2Scheduler",
            "inputs": {"steps": steps, "width": width, "height": height},
        },
        "19": {
            "class_type": "CFGGuider",
            "inputs": {
                "model": ["10", 0],
                "positive": ["13", 0],
                "negative": ["14", 0],
                "cfg": cfg,
            },
        },
        "20": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["16", 0],
                "guider": ["19", 0],
                "sampler": ["17", 0],
                "sigmas": ["18", 0],
                "latent_image": ["15", 0],
            },
        },
        "21": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["20", 0], "vae": ["12", 0]},
        },
        "22": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": save_prefix, "images": ["21", 0]},
        },
    }


def build_advanced_inpaint_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    image_filename: str,
    mask_filename: str | None = None,
    ipadapter_image_filename: str | None = None,
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 28,
    cfg: float = 5.0,
    denoising_strength: float = 1.0,
    loras: list[dict[str, Any]] | None = None,
    ipadapter_weight: float = 0.85,
    ipadapter_weight_type: str = "composition",
    ipadapter_ref_size: int = 256,
    sampler: str = "dpmpp_2m",
    scheduler: str = "karras",
    use_controlnet_depth: bool = False,
    controlnet_depth_strength: float = 0.75,
    controlnet_file: str = "controlnet-depth-sdxl-1.0.safetensors",
) -> dict[str, Any]:
    """
    SDXL inpainting with IP-Adapter Plus reference image.

    Uses InpaintModelConditioning (not VAEEncodeForInpaint) and IPAdapter attn_mask
    so the reference only affects the masked region.
    """
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    last_model: list[str | int] = ["4", 0]
    last_clip: list[str | int] = ["4", 1]

    workflow: dict[str, Any] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename},
        },
    }

    mask_node: list[str | int] | None = None
    if mask_filename:
        workflow["12"] = {
            "class_type": "LoadImage",
            "inputs": {"image": mask_filename},
        }
        workflow["13"] = {
            "class_type": "ImageToMask",
            "inputs": {"image": ["12", 0], "channel": "red"},
        }
        mask_node = ["13", 0]

    for i, lora in enumerate(loras):
        nid = str(20 + i)
        workflow[nid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": last_model,
                "clip": last_clip,
            },
        }
        last_model = [nid, 0]
        last_clip = [nid, 1]

    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": last_clip},
    }
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": last_clip},
    }

    positive_node: list[str | int] = ["6", 0]
    negative_node: list[str | int] = ["7", 0]

    if use_controlnet_depth:
        workflow["62"] = {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": controlnet_file},
        }
        workflow["63"] = {
            "class_type": "DepthAnythingPreprocessor",
            "inputs": {"image": ["10", 0], "resolution": min(width, height)},
        }
        workflow["61"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": positive_node,
                "negative": negative_node,
                "control_net": ["62", 0],
                "image": ["63", 0],
                "strength": float(controlnet_depth_strength),
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        }
        positive_node = ["61", 0]
        negative_node = ["61", 1]

    latent_image: list[str | int]
    ksampler_positive: list[str | int]
    ksampler_negative: list[str | int]

    if mask_node is not None:
        workflow["14"] = {
            "class_type": "InpaintModelConditioning",
            "inputs": {
                "positive": positive_node,
                "negative": negative_node,
                "vae": ["4", 2],
                "pixels": ["10", 0],
                "mask": mask_node,
                "noise_mask": True,
            },
        }
        ksampler_positive = ["14", 0]
        ksampler_negative = ["14", 1]
        latent_image = ["14", 2]
        denoise = 1.0
    else:
        workflow["11"] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["10", 0], "vae": ["4", 2]},
        }
        ksampler_positive = positive_node
        ksampler_negative = negative_node
        latent_image = ["11", 0]
        denoise = float(denoising_strength)

    current_model = last_model

    if ipadapter_image_filename:
        workflow["50"] = {
            "class_type": "LoadImage",
            "inputs": {"image": ipadapter_image_filename},
        }
        ref_sz = max(128, min(int(ipadapter_ref_size), 512))
        workflow["51"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["50", 0],
                "upscale_method": "lanczos",
                "width": ref_sz,
                "height": ref_sz,
                "crop": "center",
            },
        }
        workflow["53"] = {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"},
        }
        workflow["54"] = {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"},
        }
        ipa_inputs: dict[str, Any] = {
            "model": current_model,
            "ipadapter": ["54", 0],
            "image": ["51", 0],
            "weight": float(ipadapter_weight),
            "weight_type": ipadapter_weight_type,
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": 1.0,
            "embeds_scaling": "K+mean(V) w/ C penalty",
            "clip_vision": ["53", 0],
        }
        if mask_node is not None:
            ipa_inputs["attn_mask"] = mask_node
        workflow["52"] = {
            "class_type": "IPAdapterAdvanced",
            "inputs": ipa_inputs,
        }
        current_model = ["52", 0]

    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": denoise,
            "model": current_model,
            "positive": ksampler_positive,
            "negative": ksampler_negative,
            "latent_image": latent_image,
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
    }

    return workflow


def build_ipadapter_txt2img_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    guide_image_filename: str,
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 30,
    cfg: float = 5.0,
    sampler: str = "dpmpp_2m",
    scheduler: str = "karras",
    loras: list[dict[str, Any]] | None = None,
    ipadapter_weight: float = 0.72,
    ipadapter_weight_type: str = "style and composition",
    ipadapter_ref_size: int = 512,
) -> dict[str, Any]:
    """Txt2img guided by an IP-Adapter reference image (composition / style lock)."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    last_model: list[str | int] = ["4", 0]
    last_clip: list[str | int] = ["4", 1]

    workflow: dict[str, Any] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
    }

    for i, lora in enumerate(loras):
        nid = str(20 + i)
        workflow[nid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": last_model,
                "clip": last_clip,
            },
        }
        last_model = [nid, 0]
        last_clip = [nid, 1]

    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": last_clip},
    }
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": last_clip},
    }

    ref_sz = max(128, min(int(ipadapter_ref_size), 1024))
    workflow["10"] = {
        "class_type": "LoadImage",
        "inputs": {"image": guide_image_filename},
    }
    workflow["11"] = {
        "class_type": "ImageScale",
        "inputs": {
            "image": ["10", 0],
            "upscale_method": "lanczos",
            "width": ref_sz,
            "height": ref_sz,
            "crop": "center",
        },
    }
    workflow["53"] = {
        "class_type": "CLIPVisionLoader",
        "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"},
    }
    workflow["54"] = {
        "class_type": "IPAdapterModelLoader",
        "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"},
    }
    workflow["52"] = {
        "class_type": "IPAdapterAdvanced",
        "inputs": {
            "model": last_model,
            "ipadapter": ["54", 0],
            "image": ["11", 0],
            "weight": float(ipadapter_weight),
            "weight_type": ipadapter_weight_type,
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": 1.0,
            "embeds_scaling": "K+mean(V) w/ C penalty",
            "clip_vision": ["53", 0],
        },
    }

    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": ["52", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
    }

    return workflow


def build_controlnet_txt2img_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    guide_image_filename: str,
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 30,
    cfg: float = 5.0,
    sampler: str = "dpmpp_2m",
    scheduler: str = "karras",
    loras: list[dict[str, Any]] | None = None,
    depth_controlnet_file: str = "controlnet-depth-sdxl-1.0.safetensors",
    canny_controlnet_file: str = "controlnet-canny-sdxl-1.0.safetensors",
    depth_strength: float = 0.52,
    canny_strength: float = 0.62,
    canny_low_threshold: float = 0.25,
    canny_high_threshold: float = 0.6,
    preprocessor_resolution: int | None = None,
) -> dict[str, Any]:
    """Txt2img with depth + canny ControlNet maps derived from a guide image."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    last_model: list[str | int] = ["4", 0]
    last_clip: list[str | int] = ["4", 1]
    prep_res = preprocessor_resolution or max(width, height)

    workflow: dict[str, Any] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": guide_image_filename},
        },
    }

    for i, lora in enumerate(loras):
        nid = str(20 + i)
        workflow[nid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": last_model,
                "clip": last_clip,
            },
        }
        last_model = [nid, 0]
        last_clip = [nid, 1]

    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": last_clip},
    }
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": last_clip},
    }

    workflow["62"] = {
        "class_type": "ControlNetLoader",
        "inputs": {"control_net_name": canny_controlnet_file},
    }
    workflow["64"] = {
        "class_type": "ControlNetLoader",
        "inputs": {"control_net_name": depth_controlnet_file},
    }
    workflow["71"] = {
        "class_type": "Canny",
        "inputs": {
            "image": ["10", 0],
            "low_threshold": float(canny_low_threshold),
            "high_threshold": float(canny_high_threshold),
        },
    }
    workflow["72"] = {
        "class_type": "DepthAnythingPreprocessor",
        "inputs": {"image": ["10", 0], "resolution": int(prep_res)},
    }
    workflow["73"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["6", 0],
            "negative": ["7", 0],
            "control_net": ["62", 0],
            "image": ["71", 0],
            "strength": float(canny_strength),
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }
    workflow["74"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["73", 0],
            "negative": ["73", 1],
            "control_net": ["64", 0],
            "image": ["72", 0],
            "strength": float(depth_strength),
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }

    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": last_model,
            "positive": ["74", 0],
            "negative": ["74", 1],
            "latent_image": ["5", 0],
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
    }

    return workflow


def build_controlnet_ipadapter_txt2img_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    guide_image_filename: str,
    ipadapter_image_filename: str,
    width: int,
    height: int,
    seed: int | None = None,
    steps: int = 30,
    cfg: float = 5.0,
    sampler: str = "dpmpp_2m",
    scheduler: str = "karras",
    loras: list[dict[str, Any]] | None = None,
    depth_controlnet_file: str = "controlnet-depth-sdxl-1.0.safetensors",
    canny_controlnet_file: str = "controlnet-canny-sdxl-1.0.safetensors",
    depth_strength: float = 0.55,
    canny_strength: float = 0.4,
    canny_low_threshold: float = 0.25,
    canny_high_threshold: float = 0.6,
    preprocessor_resolution: int | None = None,
    ipadapter_weight: float = 0.72,
    ipadapter_weight_type: str = "style and composition",
    ipadapter_ref_size: int = 512,
) -> dict[str, Any]:
    """Txt2img with depth + canny ControlNet (pose) and IP-Adapter (identity) from guide images."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    loras = loras or []
    last_model: list[str | int] = ["4", 0]
    last_clip: list[str | int] = ["4", 1]
    prep_res = preprocessor_resolution or max(width, height)

    workflow: dict[str, Any] = {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": guide_image_filename},
        },
        "15": {
            "class_type": "LoadImage",
            "inputs": {"image": ipadapter_image_filename},
        },
    }

    for i, lora in enumerate(loras):
        nid = str(20 + i)
        workflow[nid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora.get("name") or lora.get("file"),
                "strength_model": float(lora.get("weight", 0.75)),
                "strength_clip": float(lora.get("weight", 0.75)),
                "model": last_model,
                "clip": last_clip,
            },
        }
        last_model = [nid, 0]
        last_clip = [nid, 1]

    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": last_clip},
    }
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": last_clip},
    }

    workflow["62"] = {
        "class_type": "ControlNetLoader",
        "inputs": {"control_net_name": canny_controlnet_file},
    }
    workflow["64"] = {
        "class_type": "ControlNetLoader",
        "inputs": {"control_net_name": depth_controlnet_file},
    }
    workflow["71"] = {
        "class_type": "Canny",
        "inputs": {
            "image": ["10", 0],
            "low_threshold": float(canny_low_threshold),
            "high_threshold": float(canny_high_threshold),
        },
    }
    workflow["72"] = {
        "class_type": "DepthAnythingPreprocessor",
        "inputs": {"image": ["10", 0], "resolution": int(prep_res)},
    }
    workflow["73"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["6", 0],
            "negative": ["7", 0],
            "control_net": ["62", 0],
            "image": ["71", 0],
            "strength": float(canny_strength),
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }
    workflow["74"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["73", 0],
            "negative": ["73", 1],
            "control_net": ["64", 0],
            "image": ["72", 0],
            "strength": float(depth_strength),
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }

    ref_sz = max(128, min(int(ipadapter_ref_size), 1024))
    workflow["16"] = {
        "class_type": "ImageScale",
        "inputs": {
            "image": ["15", 0],
            "upscale_method": "lanczos",
            "width": ref_sz,
            "height": ref_sz,
            "crop": "center",
        },
    }
    workflow["53"] = {
        "class_type": "CLIPVisionLoader",
        "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"},
    }
    workflow["54"] = {
        "class_type": "IPAdapterModelLoader",
        "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"},
    }
    workflow["52"] = {
        "class_type": "IPAdapterAdvanced",
        "inputs": {
            "model": last_model,
            "ipadapter": ["54", 0],
            "image": ["16", 0],
            "weight": float(ipadapter_weight),
            "weight_type": ipadapter_weight_type,
            "combine_embeds": "concat",
            "start_at": 0.0,
            "end_at": 1.0,
            "embeds_scaling": "K+mean(V) w/ C penalty",
            "clip_vision": ["53", 0],
        },
    }

    workflow["3"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": ["52", 0],
            "positive": ["74", 0],
            "negative": ["74", 1],
            "latent_image": ["5", 0],
        },
    }
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
    }
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "studio_agent", "images": ["8", 0]},
    }

    return workflow


def _resolve_face_detailer_conditioning(
    workflow: dict[str, Any],
    ksampler_node: str,
) -> tuple[list[str | int], list[str | int], list[str | int]]:
    """Return (clip, positive, negative) for FaceDetailer (plain encode, not ControlNet chain)."""
    ksampler = workflow[ksampler_node]
    positive_src = ksampler["inputs"]["positive"]
    pos_node = workflow[str(positive_src[0])]
    if pos_node.get("class_type") == "CLIPTextEncode":
        clip_src = pos_node["inputs"]["clip"]
        negative_src = ksampler["inputs"]["negative"]
        return clip_src, positive_src, negative_src
    # ControlNetApplyAdvanced output — use underlying CLIPTextEncode nodes.
    if "6" in workflow and "7" in workflow:
        clip_src = workflow["6"]["inputs"]["clip"]
        return clip_src, ["6", 0], ["7", 0]
    raise KeyError("clip")


def append_face_detailer_workflow(
    workflow: dict[str, Any],
    *,
    decode_node: str = "8",
    save_node: str = "9",
    ksampler_node: str = "3",
    seed: int = 0,
    detail_steps: int = 20,
    detail_cfg: float = 6.0,
    detail_denoise: float = 0.45,
    sampler: str = "euler_ancestral",
    scheduler: str = "normal",
    face_detector: str = "bbox/face_yolov8m.pt",
    sam_model: str = "sam_vit_b_01ec64.pth",
    guide_size: float = 384.0,
    max_size: float = 1024.0,
) -> dict[str, Any]:
    """Chain Impact Pack FaceDetailer after VAEDecode; redirect SaveImage to refined output."""
    wf = workflow
    decode = wf[decode_node]
    vae_src = decode["inputs"]["vae"]
    ksampler = wf[ksampler_node]
    model_src = ksampler["inputs"]["model"]
    clip_src, positive_src, negative_src = _resolve_face_detailer_conditioning(wf, ksampler_node)

    wf["100"] = {
        "class_type": "UltralyticsDetectorProvider",
        "inputs": {"model_name": face_detector},
    }
    wf["101"] = {
        "class_type": "SAMLoader",
        "inputs": {"model_name": sam_model, "device_mode": "AUTO"},
    }
    wf["102"] = {
        "class_type": "FaceDetailer",
        "inputs": {
            "image": [decode_node, 0],
            "model": model_src,
            "clip": clip_src,
            "vae": vae_src,
            "guide_size": guide_size,
            "guide_size_for": True,
            "max_size": max_size,
            "seed": seed,
            "steps": detail_steps,
            "cfg": detail_cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "positive": positive_src,
            "negative": negative_src,
            "denoise": detail_denoise,
            "feather": 5,
            "noise_mask": True,
            "force_inpaint": True,
            "bbox_threshold": 0.5,
            "bbox_dilation": 10,
            "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1",
            "sam_dilation": 0,
            "sam_threshold": 0.93,
            "sam_bbox_expansion": 0,
            "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False",
            "drop_size": 10,
            "bbox_detector": ["100", 0],
            "wildcard": "",
            "cycle": 1,
            "sam_model_opt": ["101", 0],
        },
    }
    wf[save_node]["inputs"]["images"] = ["102", 0]
    return wf

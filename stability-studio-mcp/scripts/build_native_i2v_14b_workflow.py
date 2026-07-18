# -*- coding: utf-8 -*-
"""Build a native ComfyUI Wan 2.1 14B I2V workflow (no WanVideoWrapper / easy-use)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "workflows" / "workflow-wan22-ti2v-5b-i2v-comfyui-native.json"
DST = ROOT / "workflows" / "workflow-wan21-i2v-14b-comfyui-native.json"
SM_DST = Path(r"D:/StabilityMatrix-win-x64/Data/Workflows") / DST.name


def main() -> None:
    wf = json.loads(SRC.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in wf["nodes"]}

    for n in wf["nodes"]:
        if n["type"] == "UNETLoader":
            n["widgets_values"] = [
                "wan2.1_i2v_480p_14B_bf16.safetensors",
                "fp8_e4m3fn",
            ]
        elif n["type"] == "VAELoader":
            n["widgets_values"] = ["wan_2.1_vae.safetensors"]
        elif n["type"] == "ModelSamplingSD3":
            n["widgets_values"] = [5.0]
        elif n["type"] == "CLIPLoader":
            # keep umt5 fp8 + wan
            pass
        elif n["type"] == "KSampler" and isinstance(n.get("widgets_values"), list):
            # [seed, ?, steps, cfg, sampler, scheduler, denoise] varies by Comfy version
            w = n["widgets_values"]
            # common UI layout: seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise
            if len(w) >= 7:
                w[2] = 24
                w[3] = 5.0
                w[4] = "uni_pc"
                w[5] = "simple"

    n55 = nodes[55]
    n55["type"] = "WanImageToVideo"
    n55["properties"] = {"Node name for S&R": "WanImageToVideo"}
    n55["widgets_values"] = [480, 832, 49, 1]
    # input order must match object_info required then optional
    n55["inputs"] = [
        {"name": "positive", "type": "CONDITIONING", "link": 110},
        {"name": "negative", "type": "CONDITIONING", "link": 111},
        {"name": "vae", "type": "VAE", "link": 105},
        {"name": "start_image", "type": "IMAGE", "shape": 7, "link": 106},
        {"name": "clip_vision_output", "type": "CLIP_VISION_OUTPUT", "shape": 7, "link": None},
    ]
    n55["outputs"] = [
        {"name": "positive", "type": "CONDITIONING", "slot_index": 0, "links": [112]},
        {"name": "negative", "type": "CONDITIONING", "slot_index": 1, "links": [113]},
        {"name": "latent", "type": "LATENT", "slot_index": 2, "links": [104]},
    ]

    # Rewire KSampler conditioning from CLIP encodes -> WanImageToVideo outputs
    ks = nodes[3]
    for inp in ks["inputs"]:
        if inp["name"] == "positive":
            inp["link"] = 112
        elif inp["name"] == "negative":
            inp["link"] = 113
        elif inp["name"] == "latent_image":
            inp["link"] = 104

    # CLIP encode outputs now feed WanImageToVideo
    nodes[6]["outputs"][0]["links"] = [110]
    nodes[7]["outputs"][0]["links"] = [111]

    # links: keep model/vae/decode/vhs; replace conditioning + i2v encode links
    keep_ids = {35, 56, 74, 75, 76, 94, 95}
    links = [L for L in wf["links"] if L[0] in keep_ids]
    links += [
        [105, 39, 0, 55, 2, "VAE"],  # vae -> WanImageToVideo.vae (slot 2)
        [106, 57, 0, 55, 3, "IMAGE"],  # image -> start_image (slot 3)
        [110, 6, 0, 55, 0, "CONDITIONING"],
        [111, 7, 0, 55, 1, "CONDITIONING"],
        [112, 55, 0, 3, 1, "CONDITIONING"],
        [113, 55, 1, 3, 2, "CONDITIONING"],
        [104, 55, 2, 3, 3, "LATENT"],
    ]
    wf["links"] = links
    wf["last_link_id"] = 113
    wf["id"] = "wan21-i2v-14b-native"
    # drop sm metadata that points at 5B
    wf.pop("sm_workflow_data", None)

    text = json.dumps(wf, indent=2)
    DST.write_text(text + "\n", encoding="utf-8")
    SM_DST.parent.mkdir(parents=True, exist_ok=True)
    SM_DST.write_text(text + "\n", encoding="utf-8")
    print("wrote", DST)
    print("wrote", SM_DST)


if __name__ == "__main__":
    main()

"""Machine-local Wan video LoRAs — copy to wan_video_loras_local.py (gitignored).

Add community LoRAs here. They merge into WAN_VIDEO_LORAS at import time.
Place .safetensors files in Stability Matrix Data/Models/Lora/.
"""

from __future__ import annotations

from typing import Any

LOCAL_WAN_VIDEO_LORAS: dict[str, dict[str, Any]] = {
    # Example — replace with your LoRA id, filename, and Hugging Face repo/path:
    # "my_concept_lora": {
    #     "id": "my_concept_lora",
    #     "filename": "my-lora.safetensors",
    #     "folder": "loras",
    #     "repo": "author/repo",
    #     "path": "my-lora.safetensors",
    #     "size_hint": "~300 MB",
    #     "default_weight": 0.8,
    #     "workflows": ["i2v_5b", "i2v_5b_painter", "v2v_5b", "v2v_5b_painter"],
    #     "purpose": "Optional community motion LoRA for 5B I2V/V2V.",
    # },
}

LOCAL_WAN_VIDEO_LORA_BUNDLES: dict[str, list[str]] = {
    # "my_bundle": ["my_concept_lora"],
}

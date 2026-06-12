# GPU hardware profile

Agents should **always** call `get_generation_context` before `generate_image` or `generate_video`. The response includes:

- **`hardware_profile`** — detected GPU, VRAM, `gpu_only`, `prefer_prompt_quality`
- **`generation_limits`** — safe caps for resolution, steps, frames, and I2V settings

Logic lives in `stability-studio-mcp/studio/hardware_profile.py`.

## Config overrides (`config.yaml`)

```yaml
hardware:
  vram_gb: 0                 # 0 = auto-detect from ComfyUI /system_stats
  gpu_only: true             # lower res/frames instead of CPU offload
  prefer_prompt_quality: true  # anatomy/face in prompt, not max pixels
```

Set `vram_gb` manually if ComfyUI is offline but you know your card (e.g. `16` for RTX 5060 Ti 16GB).

## What “high quality” means here

When `prefer_prompt_quality` is true:

- **Do** use strong prompts/negatives for face, hands, and anatomy.
- **Do not** max out resolution or frame count unless the user explicitly asks.
- **Do** stay within `generation_limits` for the detected VRAM tier.

## VRAM tiers (auto)

| VRAM | Image max | I2V default |
|------|-----------|-------------|
| ≤8 GB | 768×1024 | **`i2v_5b`**, 416×576, 49 frames @ 16fps |
| ≤12 GB | 896×1152 | **`i2v_5b`**, 480×640, 49 frames @ 16fps |
| ≤16 GB | 1024×1216 | **`i2v_5b`**, 704×1056, 65 frames @ 16fps; **`t2v`**, 81 frames @ 16fps |
| ≤24 GB | 1024×1536 | **`i2v_5b`**, 832×480, 81 frames @ 16fps |
| 32 GB+ | 1216×1664 | **`i2v_5b`** or explicit **`i2v_gpu`** |

## I2V paths

| `workflow_id` | Model | When |
|---------------|-------|------|
| **`i2v_5b`** (default) | Wan 2.2 TI2V-5B native ComfyUI | ≤16 GB, fast, clean prompts |
| **`i2v`** | Wan 2.2 14B dual + blockswap | Explicit only; heavy (~15–20 min) |
| **`i2v_gpu`** | Wan 2.1 14B builder | 24 GB+ or forced; can hang on 16 GB |

Requires **`wan2.2_ti2v_5B_fp16.safetensors`**, **`wan2.2_vae.safetensors`**, and umt5 text encoder. Run **`check_wan_assets`** / **`download_wan_assets(workflow_id="i2v_5b")`**.

## For agents

1. `get_generation_context`
2. Read `generation_limits.video_i2v` or `generation_limits.image`
3. Generate within caps
4. Only one ComfyUI instance — never launch twice (port 8188 / DB lock)
5. Avoid **parallel video jobs** on ≤16 GB — can OOM or drop ComfyUI (validated 2026-06-11)

# GPU hardware profile

Agents should **always** call `get_generation_context` before `generate_image` or `generate_video`. The response includes:

- **`hardware_profile`** — detected GPU, VRAM, `gpu_only`, `prefer_prompt_quality`
- **`generation_limits`** — safe caps for resolution, steps, frames, and I2V settings

Logic lives in `stability-studio-mcp/studio/hardware_profile.py`.

## Division of labor (main rig vs ComfyBox)

Split work by machine so agents do not overload the wrong host:

| Machine | Role | Typical work |
|---------|------|----------------|
| **Main rig** (this PC — Ryzen 7900X + RTX 5060 Ti) | CPU-heavy + local polish GPU | ffmpeg splice/concat, RIFE/interp, file ops, downloads, catalog edits, MCP orchestration, `polish_wan_video` / AnimeSharp via `.venv-post` |
| **ComfyBox** (RX 7900 XT `:8188` / Forge `:7860`) | GPU-heavy diffusion | `generate_image`, Forge refine/ADetailer, Wan `generate_video` (i2v/t2v/v2v); exclusive Comfy↔Forge switch |

Rule of thumb: **generate on ComfyBox, polish and package on the main rig.**  
`get_generation_context` returns `labor_split` with the same policy.

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
| **`i2v_5b`** (default) | Wan 2.2 TI2V-5B native ComfyUI | Drafts / SFW; often weak/censored for NSFW |
| **`i2v`** | **Wan 2.2 I2V-A14B MoE HIGH+LOW** | Explicit 14B / identity / NSFW motion |
| **`i2v_wan21_native`** | Legacy Wan 2.1 single-UNET | Fallback / A/B only — prefer `i2v` |
| **`i2v_gpu`** | Wan 2.1 14B builder | 24 GB+ or forced; can hang on 16 GB |

**`i2v` MoE wiring (MCP `studio.wan22_i2v_moe`):** HIGH UNET (+ HIGH LoRAs) → KSamplerAdv → LOW UNET (+ LOW LoRAs) → KSamplerAdv → decode. Default stacks LightX2V distill when installed; action LoRAs must be HIGH+LOW pairs (`female_orgasm`).

Assets: `check_wan_assets(workflow_id="i2v")` / `download_wan_assets` + `scripts/download_wan22_lightning_loras.py`. Orgasm NSFW LoRAs already on ComfyBox. See `stability-studio-mcp/LESSONS-WAN-I2V.md`.

## For agents

1. `get_generation_context`
2. Read `generation_limits.video_i2v` or `generation_limits.image`
3. Generate within caps
4. Only one ComfyUI instance — never launch twice (port 8188 / DB lock)
5. Avoid **parallel video jobs** on ≤16 GB — can OOM or drop ComfyUI (validated 2026-06-11)

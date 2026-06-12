---
name: "stability-studio"
description: "Local image and video generation via the stability-studio MCP server (ComfyUI through Stability Matrix). Use for ComfyUI, Stability Matrix, Wan T2V/I2V, and local SDXL generation — not hosted Media AI."
---

# Stability Studio (local ComfyUI MCP)

Copy to `%APPDATA%\Interpreter\codex-home\skills\stability-studio\SKILL.md` so local LM Studio models use MCP tools correctly.

## When to use

- ComfyUI, Stability Matrix, local image/video generation, or the stability-studio MCP.

## New users — onboarding first

This is **not** a one-click installer. Read `<PROJECT_ROOT>/onboarding/ONBOARDING.md` when the user asks to set up, install, or get started.

1. `stability-studio__get_onboarding_context` — tiers, VRAM rules, checklist
2. Ask what they want (images / video / storyboard / example only)
3. **≥ 24 GB VRAM:** ComfyUI only — do not offer Wan2GP
4. **≤ 16 GB:** ComfyUI default; Wan2GP only if user explicitly wants hero/lip sync

## Local models: do NOT call `interpreter-app`

LM Studio profiles cannot use `interpreter-app` (`unsupported call: interpreter-app`). MCP tools are exposed as `stability-studio__*`:

| Task | Tool |
|------|------|
| **Setup / onboarding** | `stability-studio__get_onboarding_context` |
| Installed models / GPU limits / families | `stability-studio__get_generation_context` |
| Missing image style files (Flux2) | `stability-studio__check_style_assets` → `stability-studio__download_style_assets` |
| ComfyUI up? | `stability-studio__check_backends` |
| Video workflow ids | `stability-studio__list_video_workflows` |
| Missing Wan models / LoRAs | `stability-studio__check_wan_assets` |
| Download Wan assets | `stability-studio__download_wan_assets` |
| Missing Wan custom nodes | `stability-studio__check_comfyui_dependencies` → `stability-studio__install_comfyui_dependencies` |
| Generate image | `stability-studio__generate_image` |
| **Edit image (preferred)** | `stability-studio__edit_image` |
| Art food groups | `stability-studio__list_art_food_groups` |
| Setup image editing | `stability-studio__setup_image_editing` |
| Generate video | `stability-studio__generate_video` |
| GPU backend check (required offline) | `stability-studio__check_gpu_backend` |
| Hero I2V (Wan2GP) | `stability-studio__check_wan2gp_runtime` → `stability-studio__generate_video_hero` |
| Clear stale GPU lock | `stability-studio__release_gpu_lock` |

**16 GB rule:** call `check_gpu_backend` before any GPU tool. Stop ComfyUI before hero Wan2GP; stop Wan2GP Gradio UI before ComfyUI video/audio.

## Video workflow ids

Use **short catalog ids only** — never the full `.json` filename:

| `workflow_id` | Mode | Notes |
|---------------|------|-------|
| *(empty)* + `mode=i2v` | image-to-video | **Default:** `i2v_5b` (Wan 2.2 TI2V-5B) |
| `i2v_5b` | image-to-video | Same as default; native ComfyUI, ~10 GB model |
| `t2v` | text-to-video | Wan 2.1 1.3B — simplest T2V path |
| `i2v` | image-to-video | Legacy Wan 2.2 **14B** dual-model (slow, 16 GB fragile) |
| `i2v_wan21` | image-to-video | Wan 2.1 VACE low-VRAM |
| `t2v_wan22` | text-to-video | Wan 2.2 T2V (extra custom nodes) |

## Image editing

Read `<PROJECT_ROOT>/IMAGE-EDITING.md` before editing an existing image.

**One-time setup:** `stability-studio__setup_image_editing()` → restart ComfyUI if required.

**Four food groups** — pass `food_group=` to `edit_image`:

| Group | Default style |
|-------|---------------|
| `anime` | ilustmix |
| `fantasy` | merged_dreams |
| `cyberpunk` | n4mik4 |
| `photoreal` | juggernaut |

```
stability-studio__edit_image(
  image_path="D:/path/photo.png",
  instruction="add small Irish flag on right church wall, keep subject identical",
  food_group="photoreal"
)
```

Preview pipeline: `stability-studio__plan_image_edit(instruction="...")`

**Photoreal** uses `juggernaut` (SDXL) or `miracle_nsfw` (Flux2) — Pony/SD1.5 photoreal checkpoints were removed.

## Recommended flows

**Image:**
```
stability-studio__get_generation_context
→ read style_readiness + architecture (sdxl | pony_sdxl | flux2_klein)
→ stability-studio__check_style_assets(style="miracle_nsfw")   # Flux2 only, if not ready
→ stability-studio__generate_image(prompt="...", style="anime")
```

**Video I2V (default path):**
```
stability-studio__get_generation_context
→ stability-studio__check_backends
→ stability-studio__check_wan_assets(workflow_id="i2v_5b")
→ stability-studio__generate_video(
     mode="i2v",
     image_path="D:/path/to/source.png",
     prompt="...",
     style="anime",
     num_frames=65,
     frame_rate=16
   )
```

Omit `workflow_id` for I2V — the server picks **`i2v_5b`** automatically. Outputs: `<PROJECT_ROOT>/stability-studio-mcp/outputs/`.

**Video V2V extend (continue from last frame):**
```
stability-studio__generate_video(
  mode="v2v",
  video_path="D:/path/to/clip.mp4",
  prompt="... continuation motion ...",
  workflow_id="v2v_5b_painter",
  num_frames=65,
  frame_rate=16
)
```
Default `concat_source=true` appends continuation to source (`*_v2v_extended.mp4`).

**Smoother I2V/V2V** (lower gait, 12fps, `smooth_character` LoRA):
```
stability-studio__generate_video(
  mode="i2v",
  image_path="...",
  prompt="walking along path, fluid leg motion",
  workflow_id="i2v_5b_painter",
  use_painter_i2v=true,
  motion_amplitude=1.2,
  smooth_motion=false
)
```

**Video T2V (81 frames max on 16 GB):**
```
stability-studio__check_backends
→ stability-studio__check_comfyui_dependencies(workflow_id="t2v")
→ stability-studio__generate_video(prompt="...", mode="t2v", workflow_id="t2v", num_frames=81, frame_rate=16)
```

**Video I2V — bow from still (`i2v_5b_painter`, motion_amplitude=1.1):**
```
stability-studio__generate_video(
  mode="i2v",
  image_path="...",
  prompt="same character, polite Japanese ojigi bow, smooth natural motion",
  workflow_id="i2v_5b_painter",
  motion_amplitude=1.1,
  num_frames=49,
  frame_rate=16,
  smooth_motion=false
)
```

## Wan asset requirements

### `i2v_5b` (default I2V)

| File | Folder | Notes |
|------|--------|-------|
| `wan2.2_ti2v_5B_fp16.safetensors` | `DiffusionModels/` | ~10 GB — `download_wan_assets(..., include_large=true)` |
| `wan2.2_vae.safetensors` | `VAE/` | Used for encode **and** decode |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `TextEncoders/` | **Required** for native `CLIPLoader` — not `umt5-xxl-enc-bf16` |

### `t2v` (Wan 2.1 T2V)

| File | Folder |
|------|--------|
| `umt5-xxl-enc-bf16.safetensors` | `TextEncoders/` |
| `wan2.1_t2v_1.3B_*.safetensors` | `DiffusionModels/` |
| `wan_2.1_vae.safetensors` | `VAE/` |

## Environment (video MP4)

Set **`VHS_USE_IMAGEIO_FFMPEG=1`** before starting ComfyUI. Install `imageio-ffmpeg` in the **ComfyUI venv** (not the MCP venv). See `OPEN-INTERPRETER-INTEGRATION.md` §6.

## Restart rules

- Edit `config.toml` or MCP code → **fully restart Open Interpreter**
- Change ComfyUI env vars → **restart ComfyUI** (and Stability Matrix if using Windows user env)

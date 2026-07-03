# Model families — agent setup guide

This document explains **what each model architecture needs**, how ComfyUI workflows differ, and which sampler/settings to use. The **machine-readable source of truth** is `stability-studio-mcp/catalog.yaml` → `model_families` and per-style `architecture` fields. Agents should call **`get_generation_context`** first; it returns `model_families`, `style_readiness`, and per-style defaults.

---

## Quick agent checklist (new PC)

1. Copy `config.yaml.example` → `config.yaml` and set Stability Matrix paths.
2. Start ComfyUI from Stability Matrix.
3. Call **`get_generation_context`** — read `style_readiness.summary` and `model_families`.
4. Before writing prompts (Jan Prompt Lab): **`get_prompt_style(style=ilustmix)`** or **`get_prompt_style(platform=pony)`** — compact grammar vs full context.
5. For **Flux2** (`miracle_nsfw`): **`check_style_assets(style="miracle_nsfw")`** → if missing, **`download_style_assets(style="miracle_nsfw", link_unet=true)`**.
5. For **Wan video**: **`check_wan_assets(workflow_id="i2v_5b")`** → **`download_wan_assets(..., include_large=true)`** if needed.
6. **Image edits:** **`setup_image_editing()`** → **`edit_image(..., food_group=...)`** — see [IMAGE-EDITING.md](IMAGE-EDITING.md).
7. Generate with **`generate_image(style=...)`** or **`generate_video(...)`** using catalog style/workflow ids only.

---

## Four art food groups

| `food_group` | Default style | Architecture | Typical use |
|--------------|---------------|--------------|-------------|
| `anime` | `ilustmix` | sdxl_anime | Illustration, Ilustmix, Illustrious |
| `fantasy` | `merged_dreams` | sdxl | Dreamy stylized portraits |
| `cyberpunk` | `n4mik4` | sdxl | Polished SDXL heroes; neon via prompt |
| `photoreal` | `juggernaut` | sdxl / flux2_klein | Juggernaut cinematic; `miracle_nsfw` Flux2 |

`list_art_food_groups()` · `get_generation_context.art_food_groups`

---

### Civitai checkpoints (e.g. `ilustmix`)

Some styles need a checkpoint that is not on disk. Catalog entry includes `download:` metadata.

1. Create a Civitai API key: https://civitai.com/user/account  
2. Add to `stability-studio-mcp/config.yaml`:
   ```yaml
   civitai:
     api_key: "YOUR_KEY"
   ```
   Or set environment variable `CIVITAI_API_TOKEN`.
3. Run **`download_style_assets(style="ilustmix")`** or:
   ```bash
   python scripts/download_style_checkpoint.py --style ilustmix
   ```
4. **Alternative:** Stability Matrix → **Models** → **Civitai** → search **iLustMix** → download **v11.1** to `StableDiffusion` as `ilustmix_v111.safetensors`.

| Style | Checkpoint | Civitai version | Size |
|-------|------------|-----------------|------|
| `ilustmix` | `ilustmix_v111.safetensors` | [v11.1](https://civitai.com/models/1110783?modelVersionId=2807896) | ~6.6 GB |

Sampler (per creator): **Euler a**, **25 steps** — set in catalog defaults.

---

## Architecture families

### SD 1.5 (`architecture: sd15`)

**Examples:** (SD 1.5 checkpoints removed from catalog — SD 1.5 ControlNet assets remain for optional use)

| Item | Value |
|------|--------|
| **Workflow** | `checkpoint_txt2img` — same nodes as SDXL |
| **Required files** | One `.safetensors` in `Data/Models/StableDiffusion/` |
| **Sampler / scheduler** | `dpmpp_2m_sde` + `karras` (CyberRealistic default) |
| **CFG / steps** | CFG ~5, steps 30 |
| **Resolution** | **512×768** native; upscaling optional |
| **Editing** | SD 1.5 ControlNet / IP-Adapter only — **not** the SDXL assets in `setup_controlnet()` |

**Common failure:** `y is None, did you try using a controlnet for SDXL on SD1?` → checkpoint is SD 1.5 but agent used SDXL ControlNet. Use `photorealistic_pony` or `juggernaut` for SDXL edit stack.

---

### SDXL (`architecture: sdxl`)

**Examples:** `juggernaut`, `merged_dreams`, `n4mik4`

| Item | Value |
|------|--------|
| **Workflow** | `checkpoint_txt2img` — `CheckpointLoaderSimple` + `KSampler` |
| **Required files** | One `.safetensors` in `Data/Models/StableDiffusion/` |
| **Sampler / scheduler** | `dpmpp_2m` + `karras` (typical) |
| **CFG / steps** | CFG 5–7, steps 28–30 |
| **Resolution** | 1024²; portrait 832×1216 common |
| **Prompts** | Comma tags; negatives work well |

**Common failure:** `CLIP input is invalid` → checkpoint is not SDXL (likely Flux or Wan).

---

### SDXL anime (`architecture: sdxl_anime`)

**Examples:** `anime`, `ilustmix`

| Item | Value |
|------|--------|
| **Extends** | SDXL |
| **Sampler / scheduler** | `euler_ancestral` + `normal` (Civitai creator default for iLustMix) |
| **Steps / CFG** | 25 steps, CFG ~6 |
| **Prompts** | `masterpiece, best quality, detailed eyes, perfect eyes`; negative `photorealistic` |
| **LoRAs** | `Eyes_for_Illustrious` + `hinaTuningFaceDetailer` (catalog defaults for `ilustmix`) |

Same single-checkpoint requirement as SDXL.

**Face detail (ADetailer equivalent):** `ilustmix` defaults **`face_detail: true`** — chains Impact Pack **FaceDetailer** after VAEDecode (YOLO `face_yolov8m.pt` + SAM). One-time: **`setup_face_detail()`** → restart ComfyUI. Override with `face_detail=false` on `generate_image` / `generate_image_i2i`. Flux2 styles skip FaceDetailer.

**I2I:** Source images are scaled to the requested `width`×`height` (lanczos) before VAE encode.

---

### Pony SDXL (`architecture: pony_sdxl`)

**Examples:** `pony` — checkpoint **`prefectPonyXL_v6.safetensors`** (Prefect Pony XL v6; official Pony V6 XL removed from this machine 2026-06-13)

| Item | Value |
|------|--------|
| **Extends** | SDXL |
| **Sampler / scheduler** | `dpmpp_2m` + `karras` |
| **CFG** | ~5.5 |
| **Prompts** | **Prefix:** `score_9, score_8_up, score_7_up` |
| **Negatives** | **Include:** `score_6, score_5, score_4` + quality/anatomy block |

Pony uses Civitai score tagging — do not use Flux-style natural-language-only prompts.

---

### Flux.2 Klein (`architecture: flux2_klein`)

**Examples:** `miracle_nsfw` (aliases: `miracle`, `flux2`)

| Item | Value |
|------|--------|
| **Workflow** | `flux2_klein_txt2img` — `UNETLoader` + `CLIPLoader` + `VAELoader` + `Flux2Scheduler` + `SamplerCustomAdvanced` |
| **Do not use** | `CheckpointLoaderSimple`, Easy-Use `fluxLoader` (no bundled CLIP on Klein merges) |
| **Sampler / scheduler** | `euler` + Flux2Scheduler (`simple` semantics) |
| **CFG / steps** | CFG ~3.5, steps ~20 |
| **Prompts** | Short natural language (40–120 words); long SDXL negatives mostly ignored |
| **VRAM** | ~12–16 GB for 9B nvfp4 at 1024² |

**Required files (9B Miracle / Klein 9B):**

| Role | Folder (Stability Matrix) | File |
|------|---------------------------|------|
| UNet | `DiffusionModels/` | `miracleinNSFWGeneration_10Nvfp4.safetensors` |
| Text encoder | `TextEncoders/` | `qwen_3_8b_fp8mixed.safetensors` |
| VAE | `VAE/` | `full_encoder_small_decoder.safetensors` |

**Important:** Klein single-file checkpoints often download into `StableDiffusion/`. ComfyUI `UNETLoader` only lists `DiffusionModels/` — **hard-link or copy** the file there. MCP tool: `download_style_assets(style="miracle_nsfw", link_unet=true)`.

**4B Klein (if added later):** text encoder `qwen_3_4b.safetensors`, VAE `flux2-vae.safetensors`, UNet in `DiffusionModels/`.

**Common failures:**

- `CLIP input is invalid: None` → SDXL workflow used on Flux checkpoint.
- `easy fluxLoader IndexError` → use native Flux2 nodes, not Easy-Use loader.
- UNet not in dropdown → link checkpoint to `DiffusionModels/`.

---

### Wan video (`architecture: wan_video`)

Not an image style — registered under `catalog.yaml` → `video_workflows`.

| Item | Value |
|------|--------|
| **Workflow** | Saved JSON in `Data/Workflows/` → converted by `workflow_converter.py` |
| **Default T2V** | `workflow_id=t2v` (Wan 2.1 1.3B) — **81 frames max** @ 16 fps on 16 GB |
| **Default I2V** | `workflow_id=i2v_5b` (Wan 2.2 TI2V-5B) — **65 frames max** @ 16 fps on 16 GB |
| **Bow from still** | `i2v_5b_painter`, `motion_amplitude=1.1`, 49 frames — see `outputs/kitsune_bow_video_test.json` |
| **Assets** | See [WAN-ASSETS.md](WAN-ASSETS.md) |
| **Env** | `VHS_USE_IMAGEIO_FFMPEG=1` before ComfyUI start (MP4) |

Tools: `check_wan_assets`, `download_wan_assets`, `check_wan_video_loras`, `download_wan_video_loras`, `check_painter_i2v_dependencies`, `check_comfyui_dependencies`.

Optional I2V: `workflow_id=i2v_5b_painter`, `lora_bundle=walk_cycle|cinematic_church`, `motion_amplitude=1.05–1.25`. See [WAN-ASSETS.md](WAN-ASSETS.md).

---

## Style → architecture map (catalog)

| Style ids | Architecture |
|-----------|----------------|
| `anime`, `ilustmix`, `ilustmix_v10` | `sdxl_anime` |
| `juggernaut`, `merged_dreams`, `artius_wan`, `n4mik4` | `sdxl` |
| `pony` (Prefect Pony XL v6) | `pony_sdxl` |
| `anime`, `ilustmix`, `animagine_xl` | `sdxl_anime` |
| `miracle_nsfw` | `flux2_klein` |

Per-style overrides (checkpoint, prompts, steps) remain in each style block under `styles:` in `catalog.yaml`.

---

## MCP tools reference

| Tool | Purpose |
|------|---------|
| `get_generation_context` | Families, styles, `style_readiness`, GPU limits |
| `check_style_assets(style=...)` | Missing SDXL checkpoint or Flux2 companion files |
| `download_style_assets(style=...)` | Fetch Flux2 text encoder/VAE; link UNet |
| `check_wan_assets` | Wan video asset manifest |
| `download_wan_assets` | Fetch Wan models from Hugging Face |

---

## Where code lives

| Concern | File |
|---------|------|
| Family definitions + style defaults | `stability-studio-mcp/catalog.yaml` |
| SDXL workflow builder | `stability-studio-mcp/studio/workflow_builder.py` → `build_txt2img_workflow` |
| Flux2 workflow builder | `workflow_builder.py` → `build_flux2_klein_txt2img_workflow` |
| Routing by architecture | `stability-studio-mcp/studio/engine.py` |
| Image asset checks / downloads | `stability-studio-mcp/studio/style_assets.py` |
| Video asset checks / downloads | `stability-studio-mcp/studio/wan_assets.py` |
| Video UI JSON conversion | `stability-studio-mcp/studio/workflow_converter.py` |

When adding a new model family: extend `model_families` in `catalog.yaml`, add workflow routing in `engine.py`, and add asset manifest entries in `style_assets.py` if companion downloads are needed.

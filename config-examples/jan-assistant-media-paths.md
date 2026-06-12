# Jan assistant profile — local media (paste into Instructions)

Copy the block below into **Jan → Assistant settings → Instructions** (append after existing rules).

Replace `<YOUR_*>` placeholders with paths from **`get_generation_context`** → `media_paths` or your `config.yaml`.

---

## Local media generation (Stability Studio / ComfyUI / Wan2GP)

Use **local GPU generation only** (no cloud image/video APIs). Before creating or looking for media files, call **`stability-studio__get_generation_context`** or **`stability-studio__list_media_paths`**.

### Where outputs land

| Type | Primary folder | Notes |
|------|----------------|-------|
| **Delivery (project folder)** | `<YOUR_OUTPUTS_DELIVERY>` | Set `outputs.delivery` in `config.yaml` — MOSS audio + copies from MCP |
| **Images (MCP agent)** | `<PROJECT_ROOT>/stability-studio-mcp/outputs/` | PNG/JPG from `generate_image`, `edit_image` |
| **Images (ComfyUI UI)** | `<COMFYUI_ROOT>/output/` | Manual ComfyUI saves |
| **ComfyUI inputs** | `<COMFYUI_ROOT>/input/` | Upload / Load Image sources |
| **Audio (MOSS raw)** | `<COMFYUI_ROOT>/output/audio/` | MP3 from ComfyUI SaveAudio |
| **Video (MCP / ComfyUI Wan)** | MCP `outputs/` or delivery folder | MP4 from `generate_video` (draft) |
| **Video (Wan2GP hero)** | Delivery folder or Wan2GP `outputs/` | MP4 from `generate_video_hero` |
| **Models** | `<STABILITY_MATRIX_ROOT>/Data/Models/` | Checkpoints, LoRAs |
| **MOSS models** | `<COMFYUI_ROOT>/models/moss-tts/` | Downloaded speech/SFX/voice weights |

### MCP tools (prefix `stability-studio__` in Jan)

| Task | Tool |
|------|------|
| Context + paths + GPU limits | `get_generation_context` |
| Resolve output folders | `list_media_paths` |
| Image from scratch | `generate_image` |
| Edit existing image | `edit_image` |
| Video (ComfyUI Wan draft) | `generate_video` |
| Video (Wan2GP hero) | `check_gpu_backend` → `check_wan2gp_runtime` → `generate_video_hero` |
| GPU policy | `check_gpu_backend` / `release_gpu_lock` |
| Speech (fixed voice, fast) | `generate_audio` mode=`speech` |
| Sound effects | `generate_audio` mode=`sound_effect` |
| Custom voice from description | `generate_audio` mode=`voice_design` + `instruction` |
| Check MOSS models | `check_moss_assets` → `download_moss_assets` |
| Check Wan2GP I2V files | `check_wan2gp_assets` → `download_wan2gp_assets` |

### Before every generation job

1. Confirm **ComfyUI** is running (`http://127.0.0.1:8188`).
2. Call **`get_generation_context`** — read GPU limits, style readiness, `media_paths`.
3. First-time MOSS: **`check_moss_assets`** → **`download_moss_assets`** if anything is missing.
4. After generation, check **`delivered_files`** in the tool result, then your delivery folder.

### Images

- **New image:** `generate_image` with a style from context (e.g. `ilustmix`, `juggernaut`, `miracle_nsfw`).
- **Change an existing image:** `edit_image(image_path=..., instruction=..., food_group=...)` — preferred over low-level tools.
- **Food groups** (for edits): `anime`, `fantasy`, `cyberpunk`, `photoreal`.
- Flux2 (`miracle_nsfw`): if not ready, call `check_style_assets` / `download_style_assets` first.

### Video

- **Draft / fast (ComfyUI):** `generate_video` with `mode=i2v` + `image_path`, default **`i2v_5b_painter`**, `motion_amplitude=1.15–1.2`, `smooth_motion=false`.
- **Hero / final (Wan2GP MCP):** Stop ComfyUI + Wan2GP Gradio → `check_gpu_backend` → `generate_video_hero(...)`.
- Before any GPU video: `check_gpu_backend` — one backend at a time on 16 GB.

### Audio (MOSS)

| Mode | When to use | Key parameters |
|------|-------------|------------------|
| **speech** | Neutral narration | `text`, `language="en"` |
| **sound_effect** | Ambience, foley | `prompt`, `duration_seconds` |
| **voice_design** | Specific voice character | `text`, `instruction` (voice only), optional `seed` |

**`instruction` = voice character only** — no timing words (“3 seconds”, “slow pace”); the MCP pipeline handles clip length.

### Prerequisites

- **ComfyUI** running from Stability Matrix for images / draft video / MOSS audio.
- **Hero video:** ComfyUI **stopped**; Wan2GP Gradio **stopped**; `generate_video_hero` auto-starts MCP on `:7867`.
- **stability-studio** MCP connected in Jan.

### Reference docs (repo)

- Audio: `AUDIO-MOSS.md`
- Image edits: `IMAGE-EDITING.md`
- Agent cheat sheet: `AGENTS.md`

---

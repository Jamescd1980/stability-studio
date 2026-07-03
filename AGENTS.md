# Agent guide — Stability Studio

Instructions for AI agents (Cursor, cloud agents, Open Interpreter) working in this repository.

## What this project is

**Stability Studio MCP** — a Python MCP server that routes natural-language style requests to **ComfyUI** (headless) using **Stability Matrix** models and saved workflow JSON. It is **not** a one-stop shop; it is meant for **AI-assisted setup** of complicated local tools. See **`onboarding/ONBOARDING.md`** for the guided path.

Supports:

- **Images** — SD 1.5 / SDXL / Pony / Flux.2 Klein via `catalog.yaml` style presets and `model_families`
- **Image editing** — **`edit_image`** (unified), i2i, inpaint, IP-Adapter, ControlNet — see [IMAGE-EDITING.md](IMAGE-EDITING.md)
- **Video** — Wan T2V/I2V via converted Stability Matrix workflows (`workflow_id=t2v` recommended)

## Four art food groups

Use `food_group=` on **`edit_image`** (or pick matching styles for T2I):

| Group | Default style | Examples |
|-------|---------------|----------|
| `anime` | `ilustmix` | `anime`, `animagine_xl` |
| `fantasy` | `merged_dreams` | `pony` |
| `cyberpunk` | `n4mik4` | `juggernaut` |
| `photoreal` | `juggernaut` | `miracle_nsfw` (Flux2) |

`list_art_food_groups()` · `get_generation_context.art_food_groups`

## Repository layout

```
studio-agent/
  stability-studio-mcp/     # MCP server package
    server.py               # Entry point
    config.yaml             # Local paths (gitignored — copy from config.yaml.example)
    catalog.yaml            # Styles, food groups, video workflows, model_families
    studio/                 # Engine, ComfyUI client, edit_pipeline, segmentation
  config-examples/          # Cursor MCP, Open Interpreter TOML, OI skill
  IMAGE-EDITING.md          # Edit playbook (primary handoff for edits)
```

## Running generation (requires local GPU stack)

Generation tools **only work when**:

1. User has cloned the repo and configured `config.yaml`
2. **ComfyUI** is running (`http://127.0.0.1:8188`)
3. MCP server is connected to the agent (Cursor local, or Open Interpreter with `[mcp_servers.stability-studio]`)

**Cloud agents** without access to the user's machine should **not** expect `generate_image` / `edit_image` to work. They can still fix bugs and update docs.

## MCP tool cheat sheet

| Tool | Use |
|------|-----|
| **`get_onboarding_context`** | **New users** — tiers, discovery questions, VRAM routing, install checklist |
| `get_generation_context` | **`model_families`**, **`art_food_groups`**, **`image_editing_readiness`**, **`face_detail_readiness`**, styles, GPU limits |
| **`edit_image`** | **Preferred** — natural-language edit (`food_group`, `instruction`) |
| `plan_image_edit` | Preview pipeline without GPU |
| `setup_image_editing` | One-shot edit stack install (~12 GB models) |
| `check_image_editing_readiness` | IP-Adapter, ControlNet, segmentation status |
| `list_art_food_groups` | Four food groups + default styles |
| `generate_image` | T2I from scratch (`face_detail` optional; default on `ilustmix`) |
| `generate_image_i2i` | Mood/lighting tweak (not for adding objects); `face_detail` optional |
| `setup_face_detail` / `check_face_detail_dependencies` | Impact Pack FaceDetailer + YOLO/SAM models (ADetailer-style pass) |
| `inpaint_advanced` | Low-level masked edit + IP-Adapter |
| `generate_image_controlnet` | Depth + canny guided T2I |
| **`setup_pose_control`** / **`check_pose_control_readiness`** | OpenPose XL2 + line preprocessors — see [POSE-CONTROL.md](POSE-CONTROL.md) |
| **`extract_control_maps`** | OpenPose / Canny / anime lineart previews from a still |
| **`generate_image_pose_guided`** | I2i + OpenPose CN — identity still + pose PNG from [editor](https://openpose-editor.vercel.app/) |
| `list_pose_control_options` | Preprocessor ids + OpenPose editor URLs |
| `sync_checkpoint_architectures` | Fix catalog vs on-disk checkpoint family |
| `check_style_assets` / `download_style_assets` | Flux2 / checkpoint manifest |
| `check_wan_video_loras` / `download_wan_video_loras` | Optional Wan motion/face/lighting LoRAs |
| `check_painter_i2v_dependencies` / `install_painter_i2v_dependencies` | PainterI2V motion node |
| `generate_video` | `mode=t2v|i2v|v2v`; auto **`applied_safety_caps`** on ≤16 GB; **`smooth_motion=false`** recommended |
| `plan_storyboard_scene` | **Hero** storyboard plan (Wan2GP + MOSS + splice) — see STORYBOARD-QUICKSTART.md |
| `check_storyboard_readiness` | MOSS + Wan2GP hero + GPU + `outputs.delivery` layout |
| **Storyboard module** | `studio/storyboard_cli.py` — reusable plan/check/splice |
| **Storyboard spreadsheet (VN)** | `studio/storyboard_sheet.py` — CSV per chapter, Ren'Py export — [STORYBOARD-SHEET.md](STORYBOARD-SHEET.md) |
| **Remote laptop (Jan → desktop GPU)** | [REMOTE-LAPTOP-SETUP.md](REMOTE-LAPTOP-SETUP.md) — `scripts/remote-laptop/` |
| **Storyboard CLI** | `scripts/storyboard/generate_storyboard.py` — `plan` / `check` / `splice` |
| **Sheet CLI** | `scripts/storyboard/manage_sheet.py` — `init` / `check` / `queue` / `export-renpy` |
| **Rin example** | [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) — Wan2GP hero + MOSS + manifest |
| `plan_scene_sequence` / `generate_scene_sequence` | Draft ComfyUI multi-beat; `execute=true` runs I2V/V2V chain |
| **GPU policy** | **`check_gpu_backend`** before GPU tools; **`release_gpu_lock`** if stale |
| **Hero I2V (Wan2GP)** | `check_wan2gp_runtime` → **`generate_video_hero`** (stop ComfyUI + Wan2GP UI first) |
| `plan_wan2gp_job` | Preview hero settings JSON (no GPU) |
| **Audio (MOSS)** | `check_moss_assets` → `download_moss_assets` → `generate_audio(mode=speech|sound_effect|voice_design)` |
| **Media paths** | `list_media_paths` or `get_generation_context.media_paths` |
| **Wan2GP assets** | `check_wan2gp_assets` / `download_wan2gp_assets` |

Outputs land in `stability-studio-mcp/outputs/` (setup JSON + scripts). Configure `outputs.delivery` for project folders: `temp/`, `images/`, `assets/`, `clips/`, `audio/`, `logs/`, `final/` — see `PATHS.md`.

## Image editing (agents)

1. **`setup_image_editing()`** once per machine → restart ComfyUI if required.
2. **`plan_image_edit(instruction=...)`** to preview pipeline.
3. **`edit_image(image_path, instruction, food_group=...)`** — read `verification.manual_checks` in the result.

Full decision tree: **[IMAGE-EDITING.md](IMAGE-EDITING.md)**

- **Photoreal** food group uses **`juggernaut`** (SDXL) or **`miracle_nsfw`** (Flux2) — SD 1.5 checkpoints removed from catalog.
- **Add object:** `hybrid_preserve` (default for “add flag…”) — not i2i.
- **Flag prompts:** green white orange vertical tricolor; negate orange-on-armor.

## Open Interpreter specifics

Local LM Studio models must call MCP tools **directly** (`stability-studio__*` prefix in OI). Install skill from `config-examples/stability-studio-skill.md`. See `OPEN-INTERPRETER-INTEGRATION.md`.

## GPU limits (always check first)

Call **`get_generation_context`** and read `hardware_profile`, `generation_limits`, `style_readiness`. Stay within limits unless the user explicitly asks for more.

## Validated working path (June 2026)

- **Images:** catalog styles (`sd15`, `sdxl`, `sdxl_anime`, `pony_sdxl`, `flux2_klein`)
- **Edits:** `setup_image_editing` → `edit_image` with food groups
- **Flux2:** `miracle_nsfw` — companion assets via `download_style_assets`
- **Video T2V:** `workflow_id=t2v` — Wan 2.1 1.3B; **81 frames max** on 16 GB (validated 2026-06-11)
- **Video I2V draft:** `mode=i2v` + `image_path` → **`i2v_5b`** / **`i2v_5b_painter`**; **65 frames max** on 16 GB
- **Video I2V hero:** **`generate_video_hero`** — Wan2GP Enhanced Lightning v2; **49 frames @ 832×480** validated (2026-06-12) — `outputs/wan2gp_bow_hero_result.json`
- **Bow from still:** hero → `generate_video_hero`; draft → `i2v_5b_painter` `motion_amplitude=1.1`, 49 frames

## Do not

- Commit `config.yaml` (personal paths)
- Use SDXL ControlNet with a non-SDXL checkpoint (run `sync_checkpoint_architectures` if unsure)
- Pass full `.json` workflow filenames as `workflow_id` — use short ids (`t2v`)

## Docs

- **Image editing:** [IMAGE-EDITING.md](IMAGE-EDITING.md)
- **Cursor:** `CURSOR-INTEGRATION.md`
- **Open Interpreter:** `OPEN-INTERPRETER-INTEGRATION.md`
- **Model families:** [MODEL-FAMILIES.md](MODEL-FAMILIES.md)
- **Restarts:** [RESTART-GUIDE.md](RESTART-GUIDE.md)
- **Windows paths:** [PATHS.md](PATHS.md)

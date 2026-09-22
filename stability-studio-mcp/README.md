# Stability Studio MCP

Python MCP server for style-aware local image and video generation via **Stability Matrix** and **ComfyUI**.

## Install

```powershell
pip install -r requirements.txt
copy config.yaml.example config.yaml
# Edit config.yaml — set stability_matrix.root and related paths
```

From repo root, `..\install.ps1` does the above automatically.

## Configure

| File | Purpose |
|------|---------|
| `config.yaml` | Machine paths and URLs (**gitignored** — copy from `config.yaml.example`) |
| `catalog.yaml` | Style presets and video `workflow_id` mappings |
| `outputs/` | Generated files copied here (gitignored except `.gitkeep`, `README.md`) |

## Run (manual test)

```powershell
python server.py
```

Normally the MCP host (Cursor, Open Interpreter) launches `server.py` via MCP config.

Maintenance CLIs: `scripts/download_wan_assets.py`, `scripts/check_asset_updates.py`, etc. See `scripts/README.md`. Dev-only tools: `scripts/dev/` (not in handoff zip).

**Workflow JSON:** files in `workflows/` must be copied to Stability Matrix `Data/Workflows/` — see [workflows/README.md](workflows/README.md).

## Integration docs

- **Cursor:** `../CURSOR-INTEGRATION.md`
- **Open Interpreter:** `../OPEN-INTERPRETER-INTEGRATION.md`
- **Agents:** `../AGENTS.md`
- **Image editing:** `../IMAGE-EDITING.md`
- **IP-Adapter / ControlNet setup:** `../IP-ADAPTER-SETUP.md`
- **GPU limits:** `../HARDWARE.md`
- **Wan models:** `../WAN-ASSETS.md`

## MCP tools

**Published count: 138** — full inventory and Jan-safe core allowlist: [../TOOLS.md](../TOOLS.md).

Root [../README.md](../README.md) has the short cheat sheet. Call `get_onboarding_context` / `get_generation_context` before browsing the full surface.


## Video prerequisites

### I2V 14B NSFW / identity — `i2v` (Wan 2.2 MoE)

Dual HIGH+LOW experts via `studio.wan22_i2v_moe` (see `LESSONS-WAN-I2V.md`).

| File | Folder |
|------|--------|
| `Wan2_2-I2V-A14B-HIGH_fp8_…_KJ.safetensors` | `DiffusionModels/I2V/` |
| `Wan2_2-I2V-A14B-LOW_fp8_…_KJ.safetensors` | `DiffusionModels/I2V/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `TextEncoders/` |
| `wan_2.1_vae.safetensors` | `VAE/` |
| LightX2V distill HIGH+LOW | `Lora/` (`download_wan22_lightning_loras.py`) |

```powershell
python scripts/download_wan_assets.py --workflow i2v --include-large
python scripts/download_wan22_lightning_loras.py
```

### I2V draft (default — `i2v_5b`)

| File | Folder |
|------|--------|
| `wan2.2_ti2v_5B_fp16.safetensors` | `DiffusionModels/` (~10 GB) |
| `wan2.2_vae.safetensors` | `VAE/` |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `TextEncoders/` |

```powershell
python scripts/download_wan_assets.py --workflow i2v_5b --include-large
```

Workflow JSON (Stability Matrix): `workflow-wan22-ti2v-5b-i2v-comfyui-native.json`

### V2V extend (`mode=v2v`, default `v2v_5b_painter`)

Same Wan 2.2 assets as I2V. MCP extracts the **last frame** of `video_path`, generates a continuation, and concat source+new by default.

```text
generate_video(mode="v2v", video_path="clip.mp4", prompt="...", workflow_id="v2v_5b_painter")
```

Workflow JSON: `workflow-wan22-ti2v-5b-v2v-comfyui-native.json` (also in `workflows/`).

### T2V (`workflow_id=t2v`)

| File | Folder |
|------|--------|
| `umt5-xxl-enc-bf16.safetensors` | `TextEncoders/` |
| `wan2.1_t2v_1.3B_*.safetensors` | `DiffusionModels/` |
| `wan_2.1_vae.safetensors` | `VAE/` |

### All video

- `imageio-ffmpeg` in ComfyUI venv + `VHS_USE_IMAGEIO_FFMPEG=1` before ComfyUI starts

## Troubleshooting

- **Missing config.yaml** — copy `config.yaml.example`
- **ComfyUI not running** — launch from Stability Matrix
- **`Cannot copy out of meta tensor`** on I2V — install `umt5_xxl_fp8_e4m3fn_scaled` (not enc-bf16) for native `i2v_5b`
- **Video: 36 channels error** — Wan model remapper (fixed in `workflow_converter.py`)
- **Video: VHS Errno 22** — ffmpeg env var (see OI integration doc §6)

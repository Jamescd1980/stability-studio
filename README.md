# Stability Studio

Local image and video generation for **Stability Matrix** + **ComfyUI**, exposed as an [MCP](https://modelcontextprotocol.io/) server for **Cursor**, **Open Interpreter**, and other agents.

Talk in plain language — *"anime portrait"*, *"juggernaut cinematic"* — the server picks checkpoints, builds workflows, and queues generation on your GPU.

## Features

- **Image generation** — SD 1.5, SDXL, Pony, Flux.2 Klein via style presets and **`model_families`**
- **Image editing** — unified **`edit_image`**, four art food groups (anime / fantasy / cyberpunk / photoreal) — [IMAGE-EDITING.md](IMAGE-EDITING.md)
- **Video generation** — Wan T2V/I2V from saved Stability Matrix workflow JSON (default I2V: **`i2v_5b`**)
- **Style catalog** — aliases, LoRAs, prompt prefixes in `catalog.yaml`
- **Workflow converter** — UI-format ComfyUI workflows → API prompts with Wan model/T5 remapping
- **Agent-ready** — MCP tools + Cursor rules + Open Interpreter skill examples

## Requirements

- [Stability Matrix](https://github.com/LykosAI/StabilityMatrix) with **ComfyUI** package
- Python 3.11+
- Models per workflow (SDXL checkpoints for images; Wan + umt5 for video — see docs)

## Quick start

**Not a one-click installer** — an MCP workflow that lets your AI assistant drive ComfyUI for you.

```powershell
git clone https://github.com/Jamescd1980/stability-studio.git
cd stability-studio
.\install.ps1
```

Copy **workflow JSON** into Stability Matrix before video/MOSS: see [`stability-studio-mcp/workflows/README.md`](stability-studio-mcp/workflows/README.md) (or `bundled-workflows/`).

1. Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` if Cursor does not auto-detect Python  
2. Open this folder in **Cursor** (or configure **Open Interpreter** — see docs below)  
3. Tell the agent: **"Help me set up Stability Studio"** — it reads the **[onboarding pack](onboarding/README.md)**  
4. When ready: launch **ComfyUI** from Stability Matrix; complete Tier 1 (images) before video  

| Audience | Start here |
|----------|------------|
| Less technical + AI assistant | [onboarding/README.md](onboarding/README.md) |
| Developers / power users | [CURSOR-INTEGRATION.md](CURSOR-INTEGRATION.md) |
| Storyboard example | [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) |

## MCP tools

| Tool | Description |
|------|-------------|
| `get_generation_context` | **`model_families`**, **`style_readiness`**, styles, GPU limits, Wan assets |
| `check_style_assets` / `download_style_assets` | Flux2 / image model manifest (companion downloads) |
| `list_styles` / `list_checkpoints` / `list_loras` | Library scan |
| `list_video_workflows` | `t2v`, `i2v_5b`, `i2v`, … |
| `check_backends` | ComfyUI / InvokeAI reachability |
| `check_wan_assets` / `download_wan_assets` | Wan model manifest check and Hugging Face download |
| `check_comfyui_dependencies` | Missing custom nodes for video |
| `install_comfyui_dependencies` | Clone known node packs |
| `edit_image` | Unified natural-language edit (`food_group=anime\|fantasy\|cyberpunk\|photoreal`) |
| `setup_image_editing` | One-shot edit stack (IP-Adapter + ControlNet SDXL/SD1.5 + segmentation) |
| `generate_image` | Style-aware T2I |
| `list_art_food_groups` | Four art food groups + default styles |
| `generate_video` | Wan T2V/I2V (ComfyUI draft); **`image_path`** required for I2V |
| `generate_video_hero` | Wan2GP Lightning v2 hero I2V (headless MCP) |
| `check_gpu_backend` | ComfyUI vs Wan2GP policy (required before GPU tools offline) |
| `get_onboarding_context` | **Start here** — tiers, questions, VRAM rules, install checklist |
| `plan_storyboard_scene` | Hero I2V + MOSS + splice plan from a short script (no GPU) |
| `check_storyboard_readiness` | MOSS + Wan2GP + GPU + project layout for storyboards |

**Storyboard (Rin example):** [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) — Wan2GP hero + MOSS + `generate_storyboard.py` (**v1.0.0-beta**)

## Documentation

| [STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md) | Linked hero clips + MOSS + splice (Rin example) |
| Doc | Audience |
|-----|----------|
| [CURSOR-INTEGRATION.md](CURSOR-INTEGRATION.md) | Cursor setup, local vs cloud agents |
| [OPEN-INTERPRETER-INTEGRATION.md](OPEN-INTERPRETER-INTEGRATION.md) | OI + LM Studio, troubleshooting, lessons learned |
| [AGENTS.md](AGENTS.md) | AI agent instructions (all platforms) |
| [HARDWARE.md](HARDWARE.md) | GPU tiers and generation limits |
| [MODEL-FAMILIES.md](MODEL-FAMILIES.md) | SD 1.5 / SDXL / Pony / Flux2 / Wan — samplers, files, agent checklist |
| [IMAGE-EDITING.md](IMAGE-EDITING.md) | Edit tools, decision tree, lessons learned, roadmap |
| [IP-ADAPTER-SETUP.md](IP-ADAPTER-SETUP.md) | IP-Adapter + ControlNet automated setup |
| [WAN-ASSETS.md](WAN-ASSETS.md) | Wan model manifest and downloads |
| [GITHUB.md](GITHUB.md) | Publish / zip checklist |
| [stability-studio-mcp/README.md](stability-studio-mcp/README.md) | Package-level detail |

## Project structure

```
studio-agent/
  .cursor/mcp.json.example      # Copy → mcp.json (gitignored)
  .cursor/rules/                # Agent rules for generation
  config-examples/              # OI TOML, Cursor JSON, OI skill
  bundled-workflows/            # Wan/MOSS JSON → copy to SM Data/Workflows/
  stability-studio-mcp/
    server.py                   # MCP entry
    catalog.yaml                # Styles + video workflow ids
    config.yaml.example         # Path template (copy → config.yaml)
    workflows/                  # Same workflow JSON + README
    studio/                     # Engine, ComfyUI client, converter
```

## Wan2GP + storyboard (Rin reference)

Linked hero sequences: walk → bow → lunge with MOSS dialogue and ffmpeg splice.

```powershell
# Plan manifest (no GPU)
python stability-studio-mcp/scripts/storyboard/generate_storyboard.py plan --title rin --script-file beats.txt

# MCP: check_storyboard_readiness → generate_video_hero (×3) → generate_audio → splice
python stability-studio-mcp/scripts/storyboard/generate_storyboard.py splice
```

Full walkthrough: **[STORYBOARD-QUICKSTART.md](STORYBOARD-QUICKSTART.md)** · Release notes: **[RELEASE.md](RELEASE.md)**

## Status

| Feature | Status |
|---------|--------|
| Image (`generate_image`) | ✅ Working |
| Video `t2v` (Wan 2.1) | ✅ 81 frames max @ 16 fps on 16 GB |
| Video `i2v_5b` | ✅ Default draft I2V — 65 frames max on 16 GB |
| **Hero I2V (Wan2GP)** | ✅ `generate_video_hero` — 49f @ 832×480 (~125 s on 16 GB) |
| **Storyboard CLI** | ✅ `studio/storyboard_cli.py` + `generate_storyboard.py` |
| Video `i2v` (14B) | ✅ Legacy; explicit `workflow_id=i2v` |
| InvokeAI image fallback | Optional |

## License

MIT — see [LICENSE](LICENSE).

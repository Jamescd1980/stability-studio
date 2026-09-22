# Stability Studio

Local image and video generation for **Stability Matrix** + **ComfyUI**, exposed as an [MCP](https://modelcontextprotocol.io/) server for **Cursor**, **Open Interpreter**, **Jan**, and other agents.

Talk in plain language — the server picks checkpoints, builds workflows, and queues work on your GPU.

**Published tool count: 138** (see [TOOLS.md](TOOLS.md)). That is the number registered in `stability-studio-mcp/server.py` in this commit — not a vibe.

## Features

- **Images** — SD 1.5 / SDXL / Pony / Flux.2 via `catalog.yaml` styles and `model_families`
- **Editing** — unified `edit_image` + food groups (anime / fantasy / cyberpunk / photoreal)
- **Video** — Wan T2V / I2V (default draft `i2v_5b`; identity/keeper path `workflow_id=i2v` MoE)
- **Health / GPU lock** — `check_gpu_backend`, queue status, unload create-brain before heavy jobs
- **Onboarding** — `get_onboarding_context` for guided setup

## Requirements

- [Stability Matrix](https://github.com/LykosAI/StabilityMatrix) with **ComfyUI**
- Python 3.11+
- Models per workflow (see [WAN-ASSETS.md](WAN-ASSETS.md), [MODEL-FAMILIES.md](MODEL-FAMILIES.md))

## Quick start

Not a one-click installer — MCP that lets an assistant drive ComfyUI.

```powershell
git clone https://github.com/Jamescd1980/stability-studio.git
cd stability-studio
.\install.ps1
```

1. Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` if needed  
2. Open in Cursor (or wire Open Interpreter / Jan)  
3. Ask: **“Help me set up Stability Studio”** → agent should call **`get_onboarding_context`**  
4. Launch ComfyUI; finish image tier before video  

| Audience | Start here |
|----------|------------|
| New / less technical | [onboarding/README.md](onboarding/README.md) + `get_onboarding_context` |
| Every generate turn | `get_generation_context` |
| Full tool inventory | [TOOLS.md](TOOLS.md) |
| Agents | [AGENTS.md](AGENTS.md) |

## How agents should use tools

**Do not bind all 138 tools into a small local model (Jan, etc.).** Prefer the **core allowlist** in [TOOLS.md](TOOLS.md) (~24 tools): context → generate/edit/video → health/lock → assets/docs.

| Group | Purpose |
|-------|---------|
| **Context** | Discover styles, limits, readiness |
| **Generate** | T2I / naming |
| **Edit** | `edit_image` and setup |
| **Video** | Wan generate + asset checks |
| **Health / lock** | GPU exclusivity — call before heavy work |
| **Assets / docs** | Downloads and studio docs |

Advanced tools (Forge refine, pose/ControlNet, storyboard, polish/splice, delivery browsers, audio, Blender) stay available to Cursor / power profiles — discover via context tools, don’t dump them into every client.

## Core MCP tools (cheat sheet)

| Tool | Description |
|------|-------------|
| `get_onboarding_context` | **Start here** — tiers, VRAM routing, checklist |
| `get_generation_context` | Styles, `model_families`, GPU limits, readiness |
| `list_styles` / `list_video_workflows` | Catalog |
| `generate_image` | Style-aware T2I |
| `edit_image` | Natural-language edit (`food_group=…`) |
| `setup_image_editing` / `check_image_editing_readiness` | Edit stack |
| `generate_video` | Wan `t2v` / `i2v` / `v2v` (extend ≠ latent clean) |
| `check_wan_assets` / `download_wan_assets` | Wan weights |
| `check_comfyui_dependencies` / `install_comfyui_dependencies` | Custom nodes |
| `check_gpu_backend` | **Required** before competing GPU backends |
| `comfy_queue_status` | Queue / busy check |
| `unload_nari_for_gpu` | Free create-brain VRAM before Wan/Forge peaks |
| `list_studio_docs` / `read_studio_doc` | Lessons and guides |

Full alphabetical list + groups: **[TOOLS.md](TOOLS.md)**.

## Companion: heat monitor

Desk overlay for generation-host GPU heat and create-brain device placement (iGPU vs discrete GPU):

→ [comfybox-heat-monitor](https://github.com/Jamescd1980/comfybox-heat-monitor)

## Documentation

| Doc | Audience |
|-----|----------|
| [TOOLS.md](TOOLS.md) | **Published tool inventory (source of truth for counts)** |
| [AGENTS.md](AGENTS.md) | Agent instructions |
| [HARDWARE.md](HARDWARE.md) | GPU tiers / labor split (scrubbed hostnames) |
| [IMAGE-EDITING.md](IMAGE-EDITING.md) | Edit playbook |
| [MODEL-FAMILIES.md](MODEL-FAMILIES.md) | Checkpoint families |
| [WAN-ASSETS.md](WAN-ASSETS.md) | Wan downloads |
| [CURSOR-INTEGRATION.md](CURSOR-INTEGRATION.md) | Cursor |
| [OPEN-INTERPRETER-INTEGRATION.md](OPEN-INTERPRETER-INTEGRATION.md) | Open Interpreter |
| [GITHUB.md](GITHUB.md) | Public vs private publish rules |
| [stability-studio-mcp/README.md](stability-studio-mcp/README.md) | Package detail |

## Project structure

```
stability-studio/
  .cursor/mcp.json.example
  config-examples/
  onboarding/
  stability-studio-mcp/
    server.py              # MCP entry — 138 @mcp.tool handlers
    catalog.yaml
    config.yaml.example
    studio/
    workflows/
  TOOLS.md                 # Inventory matching server.py
  README.md
```

Machine-local `config.yaml`, delivery folders, and ops LAN notes stay **out** of this public hub ([Private-Studio](https://github.com/Jamescd1980/Private-Studio) / local only).

## License

See repository license file if present; otherwise treat as source-available for personal / studio use unless otherwise noted.

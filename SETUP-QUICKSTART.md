# Stability Studio — quick setup (new machine)

Unpack this folder anywhere (e.g. `D:\studio-agent`).

## 1. Python

```powershell
cd studio-agent
.\install.ps1
```

Edit `stability-studio-mcp\config.yaml` — set `stability_matrix.root` to your Stability Matrix install.

## 2. ComfyUI workflows

Copy bundled workflows into Stability Matrix when needed:

```powershell
Copy-Item bundled-workflows\workflow-wan22-ti2v-5b-i2v-comfyui-native.json `
  "<STABILITY_MATRIX_ROOT>\Data\Workflows\" -ErrorAction SilentlyContinue
Copy-Item bundled-workflows\workflow-moss-*.json `
  "<STABILITY_MATRIX_ROOT>\Data\Workflows\" -ErrorAction SilentlyContinue
```

MOSS audio: use MCP `generate_audio` or load API workflow JSON from `bundled-workflows/`. See [AUDIO-MOSS.md](AUDIO-MOSS.md).

## 3. Wan models (first-time video)

```powershell
cd stability-studio-mcp
python scripts\download_wan_assets.py --workflow i2v_5b --include-large
```

Restart ComfyUI from Stability Matrix after large downloads.

## 4. Video MP4 (ffmpeg)

In ComfyUI venv:

```powershell
<STABILITY_MATRIX_ROOT>\Data\Packages\ComfyUI\venv\Scripts\pip install imageio-ffmpeg
```

Set **`VHS_USE_IMAGEIO_FFMPEG=1`** before starting ComfyUI (Stability Matrix env vars or Windows user env).

## 5. Connect your agent

| Agent | Doc |
|-------|-----|
| **Cursor** | Open this folder as workspace → `CURSOR-INTEGRATION.md` |
| **Open Interpreter** | Merge `config-examples\open-interpreter-mcp.toml` → see `OPEN-INTERPRETER-INTEGRATION.md` |

## 6. Test

Launch ComfyUI, then in chat:

```
get_generation_context → check_backends → generate_image(prompt="...", style="anime")
```

I2V:

```
check_wan_assets(workflow_id="i2v_5b")
→ generate_video(mode="i2v", image_path="...", prompt="...", num_frames=65, frame_rate=16)
```

Full docs: `README.md`, `OPEN-INTERPRETER-INTEGRATION.md`, `WAN-ASSETS.md`.

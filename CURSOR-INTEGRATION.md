# Stability Studio MCP × Cursor

Connect this MCP server to **Cursor** (local agent or cloud agent editing this repo).

## Guided setup (less technical users)

After install, tell the agent: **"Help me set up Stability Studio."**

It should call **`get_onboarding_context`** and follow **`onboarding/ONBOARDING.md`** — tiered paths (images → draft video → storyboard), VRAM-based Wan2GP rules, and plain-language troubleshooting.

## Quick setup

### 1. Install dependencies

```powershell
cd <PROJECT_ROOT>
.\install.ps1
```

Or manually:

```powershell
cd <PROJECT_ROOT>/stability-studio-mcp
pip install -r requirements.txt
copy config.yaml.example config.yaml   # edit paths
```

### 2. Configure paths

Edit `stability-studio-mcp/config.yaml` (copy from `config.yaml.example`):

- `stability_matrix.root` → your Stability Matrix install
- `comfyui.url` → usually `http://127.0.0.1:8188`

### 3. MCP in Cursor

**Option A — project config (recommended for this repo)**

Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` (gitignored) with a workspace-relative server path. On Windows, set `"command"` to your full `python.exe` if `python` is not on PATH.

**Important:** `${workspaceFolder}` must be this repo root (`studio-agent/`), not a parent drive folder.

- **File → Open Folder** → select the `studio-agent` directory, **or**
- Open **`stability-studio.code-workspace`** from this repo (same effect)

**Option B — user/global MCP**

Merge `config-examples/cursor-mcp.json` into Cursor **Settings → MCP**, replacing the `args` path with your clone location.

### 4. Runtime

1. Launch **ComfyUI** from Stability Matrix
2. For video: set `VHS_USE_IMAGEIO_FFMPEG=1` (see `OPEN-INTERPRETER-INTEGRATION.md` §6)
3. **Restart Cursor** or reload MCP after config changes
4. Confirm **Settings → MCP** shows `stability-studio` enabled

### 5. Test in chat

**Image:**
```
Call get_generation_context, then check_backends.
If ComfyUI is up, generate_image with style anime and prompt "a knight at sunset".
```

**Video T2V:**
```
get_generation_context → check_comfyui_dependencies(workflow_id="t2v")
→ generate_video(prompt="ocean waves at sunset", workflow_id="t2v", mode="t2v")
```

**Video T2V:**
```
get_generation_context → check_comfyui_dependencies(workflow_id="t2v")
→ generate_video(prompt="ocean waves at sunset", workflow_id="t2v", mode="t2v", num_frames=81, frame_rate=16)
```

**Video I2V — Japanese bow from still (draft — ComfyUI `i2v_5b_painter`):**
```
get_generation_context → check_gpu_backend → check_backends → check_wan_assets(workflow_id="i2v_5b")
→ generate_video(
     mode="i2v",
     image_path="D:/path/to/source.png",
     prompt="same anime kitsune fox girl, performing polite Japanese ojigi bow, same outfit and face, smooth natural motion",
     workflow_id="i2v_5b_painter",
     motion_amplitude=1.1,
     style="anime",
     num_frames=49,
     frame_rate=16,
     smooth_motion=false
   )
```

**Video I2V — hero bow (Wan2GP Lightning v2 — final quality):**
```
check_gpu_backend → check_wan2gp_runtime
→ generate_video_hero(
     prompt="(at 0 seconds: ...) (at 1 second: polite Japanese ojigi bow ...) (at 2 seconds: returns upright ...)",
     image_path="D:/path/to/source.png",
     video_length=49,
     motion_amplitude=1.05,
     seed=424242
   )
```
Requires ComfyUI and Wan2GP Gradio stopped. Output → `media_paths.delivery` (Desktop/New Images). Log: `outputs/wan2gp_bow_hero_result.json`.

**Video I2V (max length on 16 GB):**

Omit `workflow_id` for I2V — the server defaults to **`i2v_5b`**.

---

## Cursor agent vs cloud agent

| Agent type | MCP generation | Notes |
|------------|----------------|-------|
| **Cursor local** (this machine) | ✅ If ComfyUI running | MCP subprocess runs locally; tools call `127.0.0.1:8188` |
| **Cloud / background agent** | ❌ Usually no | No access to your GPU or ComfyUI; use for code/docs only |
| **Cursor Tab on this repo** | Same as local | Workspace must be repo root; MCP from `.cursor/mcp.json` |

Cloud agents can still read `AGENTS.md`, `.cursor/rules/`, and integration docs to implement fixes. Actual `generate_*` calls require the user's local stack.

---

## Project rules

`.cursor/rules/stability-studio-mcp.mdc` — reminds the agent to use MCP tools for generation and documents prerequisites.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP server not listed | Open repo root as workspace; check `.cursor/mcp.json` path |
| `config.yaml` not found | `copy config.yaml.example config.yaml` and edit |
| ComfyUI not running | Launch from Stability Matrix |
| Video fails at VHS | `VHS_USE_IMAGEIO_FFMPEG=1` + restart ComfyUI |
| I2V meta tensor error | Install `umt5_xxl_fp8_e4m3fn_scaled` for `i2v_5b` |
| Tools not visible / count stuck at 51 | **Kill orphan MCP processes** (see below), toggle MCP off→on, **new Agent chat** |
| Tool count should be **58** (v0.3.0) | `get_generation_context` must include `studio_version` + `gpu_backend_policy` |

Full troubleshooting: `OPEN-INTERPRETER-INTEGRATION.md`.

---

## Files

| File | Purpose |
|------|---------|
| `.cursor/mcp.json.example` | Template → copy to gitignored `mcp.json` |
| `config-examples/cursor-mcp.json` | Template for global MCP merge |
| `AGENTS.md` | Instructions for all AI agents |

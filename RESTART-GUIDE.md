# Restart guide — ComfyUI, MCP, Open Interpreter

Agents forget restarts. Use this decision tree after **any** setup or failure.

## Quick decision tree

```
Did you install custom nodes or download large models?
├─ YES → Restart ComfyUI from Stability Matrix (always)
│         Did you change MCP server code or .cursor/mcp.json?
│         └─ YES → Restart MCP in Cursor (Settings → MCP → Restart) or new Agent chat
│
Did generation fail with "connection lost" / OOM / missing node?
├─ connection lost → Restart ComfyUI; check no parallel GPU jobs (Wan2GP + ComfyUI)
├─ OOM → Restart ComfyUI to free VRAM; lower frames; one video job at a time
├─ missing node → install_comfyui_dependencies → Restart ComfyUI
│
Did you set VHS_USE_IMAGEIO_FFMPEG=1 or edit Stability Matrix env vars?
└─ YES → Restart ComfyUI (env is read at process start)

Did you edit stability-studio-mcp Python code?
└─ YES → Restart MCP server; stale Agent chats may keep old tool list — start new chat

Open Interpreter only:
└─ Edit config.toml or MCP path → fully quit and restart Open Interpreter
```

## What requires which restart

| Change | ComfyUI | MCP (Cursor) | New Agent chat | OI restart |
|--------|---------|--------------|----------------|------------|
| `setup_image_editing()` | **Yes** | Optional | If tools missing | Yes |
| `setup_face_detail()` | **Yes** | Optional | If tools missing | Yes |
| `install_painter_i2v_dependencies()` | **Yes** | No | No | Yes |
| `download_wan_assets` (large) | **Yes** after download | No | No | No |
| `download_moss_assets` | **Yes** after download | No | No | No |
| `VHS_USE_IMAGEIO_FFMPEG=1` | **Yes** | No | No | No |
| Edit `server.py` / engine | No | **Yes** | **Recommended** | Yes |
| Duplicate MCP registration | No | **Fix config** | **Yes** | Yes |

## Parallel GPU jobs (16 GB)

**Never run ComfyUI video/audio generation while Wan2GP (or another agent) uses the GPU.**

Symptoms: `vram_free_gb: 0`, ComfyUI connection lost, MCP timeout.

Fix: Wait for the other job to finish, restart ComfyUI, run **one** generation at a time.

### GPU backend enforcement (MCP)

Stability Studio enforces **one GPU consumer** on ≤16 GB via `check_gpu_backend`:

| Backend | Tool | Requires |
|---------|------|----------|
| Draft video / audio | `generate_video`, `generate_audio` | ComfyUI running; Wan2GP **Gradio UI** stopped |
| Hero I2V | `generate_video_hero` | ComfyUI **stopped**; Wan2GP Gradio stopped; MCP on `:7867` (auto-start) |

**Offline agents (Jan, LM Studio):** must call `check_gpu_backend` before any GPU tool. Conflicts return `gpu_backend_conflict` with `blocks` and `recommendation`.

Lock file during jobs: `outputs/.gpu_backend.lock` — stale lock → `release_gpu_lock()`.

### Wan2GP hero workflow

1. Stop ComfyUI from Stability Matrix.
2. Stop Wan2GP Gradio UI (`:7860`) if open — hero uses headless MCP on `:7867`.
3. `check_wan2gp_runtime` → `generate_video_hero(prompt=..., image_path=...)`.
4. MCP auto-starts Wan2GP venv with `SETUPTOOLS_USE_DISTUTILS=stdlib` and `FASTMCP_PORT=7867`.
5. After hero completes, restart ComfyUI for image edits / draft I2V.

If auto-start fails: ensure Git is installed (`git.exe` on PATH) and Wan2GP venv intact.

Optional: `plan_wan2gp_job` previews settings JSON without GPU.

## Verify after restart

```text
check_backends → get_generation_context
check_comfyui_dependencies(workflow_id="t2v")
check_moss_assets
```

See also: `outputs/mcp_connection_diagnosis.json` for duplicate MCP server issues.

### Orphan MCP processes (Windows)

Cursor **Restart** sometimes leaves old `server.py` running. Symptom: tool count stuck (e.g. **51** instead of **58**), missing `check_gpu_backend` / `generate_video_hero`.

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'studio-agent.*server\.py' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Then: Settings → MCP → disable **stability-studio** → enable → **start a new Agent chat**.

Verify: `get_generation_context` includes `studio_version` (0.3.0) and `gpu_backend_policy`.


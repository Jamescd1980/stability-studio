# Desktop handoff from laptop — Stability Studio remote generation

**From:** Laptop Cursor agent  
**To:** Desktop Cursor agent  
**Date:** 2026-07-01 (updated 2026-07-02)  
**Placeholders:** `<DESKTOP_HOSTNAME>`, `<DESKTOP_LAN_IP>`, `<WINDOWS_USER>`, `<PROJECT_ROOT>`

---

## Executive summary

The **laptop is ready** to drive remote image generation via the `stability-studio` MCP. ComfyUI on the desktop is reachable and a live smoke test succeeded.

**Initial blocker (2026-07-01):** SMB share `StudioBata` was not reachable from the laptop — PNGs saved to laptop `outputs/` only. **Fix:** run `scripts/remote-laptop/setup_shared_images_elevated.cmd` on the desktop, map `Z:` on the laptop, set `outputs.delivery: "Z:/"`.

---

## What the laptop agent completed

### Python + MCP (laptop)

| Item | Value |
|------|-------|
| Python | `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (3.12.x) |
| MCP packages | mcp, PyYAML, requests (via `setup_laptop_jan.ps1`) |
| Laptop repo | `<LAPTOP_PROJECT_ROOT>` (e.g. OneDrive or flash-drive copy) |
| MCP config | `stability-studio-mcp\config.yaml` → remote ComfyUI |

### Jan MCP (laptop)

- Merge `config-examples/laptop-remote/jan-mcp-stability-studio.json.template`
- `stability-studio`: **active=true**
- `toolCallTimeoutSeconds`: **600** (was 30 — required for generation)
- `PYTHONUNBUFFERED`: **1**

### Remote ComfyUI — verified OK

```powershell
Invoke-WebRequest -Uri "http://<DESKTOP_LAN_IP>:8188/system_stats" -UseBasicParsing -TimeoutSec 10
```

- ComfyUI version: **0.27.0** (validated)
- Smoke test: `generate_image` style `anime` ~22s, 808×1216

### Smoke test result (before Z: delivery)

| Field | Value |
|-------|-------|
| Style | `anime` |
| Time | ~22 seconds |
| Save path (pre-share) | `stability-studio-mcp\outputs\studio_agent_*.png` |
| Save path (post-share) | `Z:\images\studio_agent_*.png` |

---

## Desktop agent action checklist

### 1. Run desktop setup scripts

```powershell
cd <PROJECT_ROOT>
.\scripts\remote-laptop\install_comfyui_lan_launcher.ps1   # close Stability Matrix first
.\scripts\remote-laptop\setup_desktop_for_laptop_jan.ps1
.\scripts\remote-laptop\setup_shared_images_elevated.cmd   # Administrator
```

### 2. Confirm ComfyUI listens on LAN

```powershell
netstat -ano | findstr :8188
```

Must include **0.0.0.0:8188**. Launch from Stability Matrix (`studio_launch.py` shim — do **not** add `--listen` in SM extra args).

### 3. Confirm SMB share

```powershell
Get-SmbShare -Name StudioBata
```

### 4. Verify

```powershell
.\scripts\remote-laptop\verify_desktop_handoff.ps1
Test-Path \\localhost\StudioBata\images
```

---

## After desktop fixes — laptop maps Z:

```powershell
.\scripts\remote-laptop\map_studio_share.ps1
# Or: net use Z: \\<DESKTOP_LAN_IP>\StudioBata /user:<DESKTOP_HOSTNAME>\<WINDOWS_USER> /persistent:yes
```

Set laptop `outputs.delivery: "Z:/"` in MCP config.

---

## Architecture

```
LAPTOP                              DESKTOP
  Jan + MCP  --HTTP-->  ComfyUI :8188  (WORKING)
  delivery   --SMB-->   StudioBata     (after elevated share setup)
```

**VRAM rule:** Laptop prompts only. Desktop generates only.

---

## Desktop config — do NOT overwrite with laptop config

Desktop `stability-studio-mcp/config.yaml` is local (`127.0.0.1`, Wan2GP, API keys). Laptop config points at LAN IP + `Z:/`.

If desktop Jan has stability-studio MCP, set **active: false** there.

---

*End of handoff — laptop agent 2026-07-01, desktop merge 2026-07-02.*

# Laptop setup — instructions for Cursor

**You are on the laptop.** Finish this machine so **Jan** drives `generate_image` on the **desktop** GPU.

Replace `<DESKTOP_HOSTNAME>` and `<DESKTOP_LAN_IP>` with values from the desktop operator.

---

## Fast path

```powershell
cd <PACKAGE_ROOT>   # folder containing studio-agent/ and packaging/
$env:STUDIO_DESKTOP_HOST = "<DESKTOP_HOSTNAME>"
$env:STUDIO_DESKTOP_IP   = "<DESKTOP_LAN_IP>"
Set-ExecutionPolicy -Scope Process Bypass
.\packaging\laptop-remote\INSTALL.ps1
```

Or step-by-step from repo root:

```powershell
.\scripts\remote-laptop\map_studio_share.ps1
.\scripts\remote-laptop\setup_laptop_jan.ps1
```

---

## Preflight

```powershell
Invoke-WebRequest "http://<DESKTOP_LAN_IP>:8188/system_stats" -UseBasicParsing -TimeoutSec 10
Test-Path "Z:\images"
```

---

## Jan

1. Merge `config-examples/laptop-remote/jan-mcp-stability-studio.json.template`
2. Read `config-examples/laptop-remote/JAN-MCP-NOTES.md` — **toolCallTimeoutSeconds: 600**
3. Paste `jan-assistant-instructions.md` into Studio Copilot
4. Restart Jan

---

## Cursor

Open **`studio-agent`** as workspace. Enable **stability-studio** MCP. Use `.cursor/mcp.json.example` as template.

---

## Verify

| Test | Expected |
|------|----------|
| `Z:\images` | Opens in Explorer |
| `get_generation_context` | ComfyUI stats |
| `generate_image` anime | PNG in `Z:\images` |

First-win prompt:

> Call get_generation_context. If ComfyUI is up, generate_image with style anime and prompt "a knight at sunset, masterpiece".

---

Full reference: `config-examples/laptop-remote/README.md` and `LESSONS-LEARNED.md`.

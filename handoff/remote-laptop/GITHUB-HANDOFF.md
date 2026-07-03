# GitHub merge handoff — desktop agent

Read after receiving `studio-agent.zip` or merging laptop handoff work.

**Scrub before push:** no `config.yaml`, no API keys, no `C:\Users\...` paths in tracked files.

---

## What's in `studio-agent.zip`

| Path | Purpose |
|------|---------|
| `REMOTE-LAPTOP-SETUP.md` | Remote laptop index |
| `scripts/remote-laptop/` | LAN ComfyUI shim, SMB share, laptop map |
| `config-examples/laptop-remote/` | Laptop MCP templates |
| `handoff/remote-laptop/` | Agent docs + `LESSONS-LEARNED.md`, `DESKTOP-HANDOFF-FROM-LAPTOP.md` |
| `packaging/laptop-remote/` | `INSTALL.ps1` distribution package |

---

## Merge into git clone

```powershell
Expand-Archive -Path studio-agent.zip -DestinationPath D:\handoff-incoming -Force
robocopy D:\handoff-incoming\studio-agent D:\studio-agent /E /XD .git __pycache__ .venv unsloth_compiled_cache /XF config.yaml mcp.json config.generated.yaml *.png *.gguf
cd D:\studio-agent
git status
git diff
```

**Do not stage:** `stability-studio-mcp/config.yaml`, `.cursor/mcp.json`, `outputs/local/`, `*.png`, `config.generated.yaml`.

---

## Suggested commit message

```
Add remote laptop generation: Jan on laptop, ComfyUI on desktop.

- scripts/remote-laptop/ with studio_launch.py SM shim
- SMB share setup, Z: drive mapping, handoff docs
- packaging/laptop-remote/INSTALL.ps1 for laptop one-click setup
```

---

## Pre-push grep

```powershell
git grep -i "api_key" -- ':!*.example' ':!*.template' ':!catalog.yaml'
git grep -E "C:\\\\Users\\\\|192\.168\.|civitai"
```

Redact machine-specific IPs, hostnames, and usernames in docs if they slipped in.

---

## Desktop after merge

1. Keep local `stability-studio-mcp/config.yaml` (127.0.0.1, Wan2GP, keys).
2. Re-run if needed:

```powershell
.\scripts\remote-laptop\install_comfyui_lan_launcher.ps1
.\scripts\remote-laptop\verify_desktop_handoff.ps1
```

---

See `handoff/remote-laptop/LESSONS-LEARNED.md` for pitfalls (SM `-- listen` typo, Jan timeout 600, map Z: by IP).

# Remote laptop generation — validated status

**Date:** 2026-07-02  
**Architecture:** Jan + MCP on laptop → ComfyUI + GPU on desktop → images via SMB share `StudioBata`

---

## End state (both machines)

| Component | Status |
|-----------|--------|
| ComfyUI LAN `http://<DESKTOP_LAN_IP>:8188` | Working with `studio_launch.py` |
| Remote `generate_image` from laptop | Working (~22s smoke test) |
| SMB `\\<DESKTOP_LAN_IP>\StudioBata` | Working (prefer IP over hostname) |
| Map `Z:` + `outputs.delivery: Z:/` | Recommended for laptop MCP |
| Jan `toolCallTimeoutSeconds` | **600** (not 30) |

---

## Desktop responsibilities

```powershell
cd <PROJECT_ROOT>
.\scripts\remote-laptop\install_comfyui_lan_launcher.ps1   # close Stability Matrix first
.\scripts\remote-laptop\setup_shared_images_elevated.cmd     # Administrator
.\scripts\remote-laptop\verify_desktop_handoff.ps1
```

Launch ComfyUI from Stability Matrix only. Do **not** add `--listen` in SM Extra Launch Arguments.

---

## Laptop responsibilities

```powershell
cd <PROJECT_ROOT>
.\scripts\remote-laptop\map_studio_share.ps1
# Or full package: packaging\laptop-remote\INSTALL.ps1
```

Copy `config-examples/laptop-remote/config.yaml.template` → `stability-studio-mcp/config.yaml` and set desktop IP.

---

## Jan MCP settings (laptop)

Merge `config-examples/laptop-remote/jan-mcp-stability-studio.json.template` into Jan MCP config.

Also set in Jan MCP settings (global):

```json
"mcpSettings": {
  "toolCallTimeoutSeconds": 600
}
```

---

## Files scrubbed for GitHub

No hostnames, LAN IPs, Windows usernames, or API keys in committed templates. Machine-specific values live in local `config.yaml` / `config.generated.yaml` (gitignored).

---

*Merged desktop + laptop handoff — Stability Studio.*

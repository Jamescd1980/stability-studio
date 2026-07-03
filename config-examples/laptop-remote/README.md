# Laptop remote generation — config & templates

Jan on the **laptop** calls `generate_image` on the **desktop** ComfyUI over LAN. Images land in a shared SMB folder.

Replace placeholders in templates before use:

| Placeholder | Example |
|-------------|---------|
| `<DESKTOP_HOSTNAME>` | `DESKTOP-YourPC` |
| `<DESKTOP_LAN_IP>` | `192.168.1.100` |
| `<DELIVERY_UNC>` | `\\\\DESKTOP-YourPC\\StudioBata` |
| `<PYTHON_EXE>` | `C:\\Users\\You\\...\\python.exe` |
| `<PROJECT_ROOT>` | `D:\\studio-agent` |

## Files in this folder

| File | Use |
|------|-----|
| `config.yaml.template` | Copy → `stability-studio-mcp/config.yaml` on **laptop** |
| `jan-mcp-stability-studio.json.template` | Merge into Jan `mcp_config.json` |
| `jan-assistant-instructions.md` | Paste into Studio Copilot instructions |

## Desktop scripts

From repo root — see [REMOTE-LAPTOP-SETUP.md](../../REMOTE-LAPTOP-SETUP.md):

| Script | Purpose |
|--------|---------|
| `scripts/remote-laptop/install_comfyui_lan_launcher.ps1` | SM `studio_launch.py` + LAN bind |
| `scripts/remote-laptop/setup_desktop_for_laptop_jan.ps1` | Firewall, laptop config template |
| `scripts/remote-laptop/setup_shared_images_elevated.cmd` | SMB share `StudioBata` |
| `scripts/remote-laptop/verify_desktop_handoff.ps1` | Post-setup checks |

## Laptop scripts

| Script | Purpose |
|--------|---------|
| `scripts/remote-laptop/map_studio_share.ps1` | Map `Z:` to desktop share |
| `scripts/remote-laptop/setup_laptop_jan.ps1` | pip install + smoke tests |

## ComfyUI + Stability Matrix

**Do not** add `--listen` in Stability Matrix **Extra launch arguments** — SM saves `-- listen` (with a space) and ComfyUI crashes.

Use **`studio_launch.py`** via `install_comfyui_lan_launcher.ps1`. It forwards SM args to `main.py` and appends a valid `--listen`.

After ComfyUI package updates, re-run `install_comfyui_lan_launcher.ps1`.

## Shared folder layout

Under `outputs.delivery` / `StudioBata`:

| Subfolder | Contents |
|-----------|----------|
| `images/` | Finished stills |
| `images/chain/` | I2V handoff frames |
| `temp/` | Raw saves pending review |
| `logs/` | `prompt_log.jsonl` |
| `final/` | Assembled deliverables |

## Workflow

| Step | Tool | Where |
|------|------|-------|
| Brainstorm | `log_image_prompt` | Laptop Jan |
| Generate | `generate_image` | Laptop → desktop GPU |
| Review | Explorer `Z:\images` | Either |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `unrecognized arguments: -- listen` | Remove listen from SM extra args; run `install_comfyui_lan_launcher.ps1` |
| Laptop cannot open desktop IP:8188 | `verify_desktop_handoff.ps1` on desktop; restart ComfyUI from SM |
| Share not found | `setup_shared_images_elevated.cmd` on desktop; map `Z:` on laptop |
| PNG only on laptop `outputs/` | Set `outputs.delivery` to `Z:/` in laptop config |

## Security

- ComfyUI has no login — home LAN only; do not port-forward 8188.
- SMB share uses Private network firewall profile.

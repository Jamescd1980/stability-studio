# Remote laptop setup (Jan prompts → desktop GPU)

Use a **laptop** for Jan / prompt writing and a **desktop** for ComfyUI generation. Saves VRAM on the desktop.

| Role | Machine | Runs |
|------|---------|------|
| Prompt Lab | Laptop | Jan + `stability-studio` MCP (stdio) |
| Generation | Desktop | Stability Matrix + ComfyUI |

```
Laptop                              Desktop
  Jan + MCP  ──HTTP──►  ComfyUI :8188  (LAN)
  delivery   ──SMB───►  \\<DESKTOP_HOST>\StudioBata
```

**Full guide:** [config-examples/laptop-remote/README.md](config-examples/laptop-remote/README.md)

## Desktop (one-time)

```powershell
cd <PROJECT_ROOT>
.\scripts\remote-laptop\install_comfyui_lan_launcher.ps1   # close Stability Matrix first
.\scripts\remote-laptop\setup_desktop_for_laptop_jan.ps1
.\scripts\remote-laptop\setup_shared_images_elevated.cmd   # Administrator
```

Launch ComfyUI from **Stability Matrix** (uses `studio_launch.py` — do **not** add `--listen` in SM extra args).

Verify: `.\scripts\remote-laptop\verify_desktop_handoff.ps1`

## Laptop (one-time)

See [handoff/remote-laptop/LAPTOP-CURSOR-SETUP.md](handoff/remote-laptop/LAPTOP-CURSOR-SETUP.md) (flash-drive / Cursor handoff).

```powershell
.\scripts\remote-laptop\map_studio_share.ps1
copy config-examples\laptop-remote\config.yaml.template stability-studio-mcp\config.yaml
# Edit desktop IP + hostname in config.yaml
```

## Handoff zip

```powershell
python stability-studio-mcp/scripts/build_handoff_zip.py
```

Includes `scripts/remote-laptop/`, `packaging/laptop-remote/`, `handoff/remote-laptop/`, and config templates.

## GitHub

Machine-specific values (LAN IP, hostname, delivery paths, API keys) stay in **local `config.yaml`** only. See [handoff/remote-laptop/GITHUB-HANDOFF.md](handoff/remote-laptop/GITHUB-HANDOFF.md) before push.

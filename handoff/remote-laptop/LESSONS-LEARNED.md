# Lessons learned — remote laptop generation

Validated **2026-07-02** on a two-machine setup: Jan + MCP on the laptop, ComfyUI on the desktop.

Placeholders: `<DESKTOP_HOSTNAME>`, `<DESKTOP_LAN_IP>`, `<WINDOWS_USER>`, `<PROJECT_ROOT>`.

---

## What worked

### Remote ComfyUI over HTTP

- Laptop MCP → `http://<DESKTOP_LAN_IP>:8188` works when desktop ComfyUI binds LAN (`0.0.0.0:8188`) and firewall allows **Private** profile on port **8188**.
- Use **`studio_launch.py`** via `scripts/remote-laptop/install_comfyui_lan_launcher.ps1` — do **not** add `--listen` in Stability Matrix Extra Launch Arguments (SM saves `-- listen` with a space and ComfyUI rejects it).
- Smoke test: `generate_image` style `anime` ~22–25s on ComfyUI v0.27.0.

### SMB delivery via mapped drive (prefer IP over hostname)

- `\\<DESKTOP_HOSTNAME>\StudioBata` may fail from the laptop; `\\<DESKTOP_LAN_IP>\StudioBata` is more reliable after desktop share setup.
- Map **`Z:`** with IP and credentials once:

```powershell
net use Z: \\<DESKTOP_LAN_IP>\StudioBata /user:<DESKTOP_HOSTNAME>\<WINDOWS_USER> /persistent:yes
```

- Set laptop MCP `outputs.delivery: "Z:/"` — more reliable than UNC strings in YAML on Windows.
- Finished PNGs land in `Z:\images\`.

### Jan MCP timeouts

- Default `toolCallTimeoutSeconds: 30` in Jan is too low for `generate_image`.
- Set **600** in Jan MCP settings (match `comfyui.timeout_seconds` in laptop `config.yaml`).
- Set `PYTHONUNBUFFERED: "1"` in MCP env.

### Cursor MCP paths

- Project `.cursor/mcp.json` needs workspace root = **`studio-agent`** for `${workspaceFolder}`.
- Optional user-global `~/.cursor/mcp.json` with absolute paths if opening other folders.

### vlm-prompt-training (separate repo — optional on laptop)

- Unzip to a short path (e.g. `C:\vlm-prompt-training`) — long OneDrive paths can break pip/Jupyter.
- Desktop-built `.venv` breaks on laptop (wrong Python path). **Recreate venv** with `setup_env.ps1` on the laptop.
- `install_jan_studio_pack.ps1` hardlinks GGUF into Jan; assistant install can use system Python if venv is broken.
- Not included in `studio-agent.zip` — ship as its own repo or release asset.

---

## Pitfalls

| Issue | Fix |
|-------|-----|
| SM Extra Launch Args `--listen` | Use `studio_launch.py` shim only |
| `INSTALL.ps1` UTF-8 without BOM on PS 5.1 | Save UTF-8 BOM or use ASCII; prefer PowerShell 7+ |
| Windows Store `python` stub | Use full path to `Python312\python.exe` |
| `net use Z:` without `/user:` | User must enter desktop password once interactively |
| Hostname UNC fails | Use LAN IP for `net use` and preflight |
| Desktop `config.yaml` overwritten | Laptop and desktop configs are **different files** |
| Jan + ComfyUI same GPU | Never — laptop prompts only, desktop generates only |
| `clean_outputs.py` vs delete | Moves strays to `outputs/local/` — delete that folder before zipping handoff |
| Long OneDrive paths for vlm | Clone vlm repo to `C:\vlm-prompt-training` or enable Windows long paths |

---

## Desktop vs laptop config split

| Machine | `comfyui.url` | `outputs.delivery` |
|---------|---------------|-------------------|
| Laptop | `http://<DESKTOP_LAN_IP>:8188` | `Z:/` |
| Desktop | `http://127.0.0.1:8188` | Local project folder |

Desktop `config.yaml` may include Wan2GP, Civitai key, etc. — **do not commit** or copy to laptop.

---

## Verification checklist

| # | Test | Expected |
|---|------|----------|
| 1 | Laptop browser `http://<DESKTOP_LAN_IP>:8188` | ComfyUI UI |
| 2 | `Test-Path Z:\images` | True |
| 3 | Jan `get_generation_context` | ComfyUI reachable |
| 4 | Jan `generate_image` | PNG in `Z:\images` |
| 5 | Desktop `verify_desktop_handoff.ps1` | All OK |

---

## Key repo paths

| Path | Purpose |
|------|---------|
| `scripts/remote-laptop/` | Desktop + laptop setup scripts |
| `config-examples/laptop-remote/` | Templates (no secrets) |
| `handoff/remote-laptop/` | Flash-drive / agent docs |
| `handoff/remote-laptop/DESKTOP-HANDOFF-FROM-LAPTOP.md` | Laptop → desktop session notes |
| `packaging/laptop-remote/INSTALL.ps1` | One-click laptop installer |
| `REMOTE-LAPTOP-SETUP.md` | Entry index |

---

*Stability Studio — remote generation handoff.*

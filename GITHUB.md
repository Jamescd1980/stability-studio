# Publishing to GitHub

Checklist when packaging this repo for public release or sharing a zip.

## Before first commit / zip

1. **`config.yaml`** — must stay gitignored (personal Stability Matrix paths, API keys). Ship only `config.yaml.example`.
2. **`outputs/`** — only `.gitkeep` and `README.md` in git; run `python stability-studio-mcp/scripts/clean_outputs.py` to move personal JSON/logs/media to `outputs/local/` (gitignored).
3. **`.cursor/mcp.json`** — gitignored; ship `.cursor/mcp.json.example` and `config-examples/cursor-mcp.json`. Recipients copy and set their Python executable if `python` is not on PATH.
4. **`studio-agent.zip`** — gitignored; built by `build_handoff_zip.py` (not committed). No `studio-agent-setup.zip` in the repo.
5. **`wan_video_loras_local.py`** — gitignored; ship `wan_video_loras_local.example.py` only.
6. **Absolute paths** — grep for `C:\Users\`, LAN IPs, hostnames, `D:/StabilityMatrix` in tracked files. Dev scripts live under `scripts/dev/` (excluded from zip). See `handoff/remote-laptop/GITHUB-HANDOFF.md` for remote-laptop scrub.
7. **Workflow JSON** — copy bundled graphs into Stability Matrix `Data/Workflows/` (see `stability-studio-mcp/workflows/README.md` and `bundled-workflows/`).
8. **Clone URL** — [https://github.com/Jamescd1980/stability-studio](https://github.com/Jamescd1980/stability-studio) (see root `README.md`).

## Initialize and push

```powershell
cd <PROJECT_ROOT>
git init
git add .
git status   # verify config.yaml, outputs/*, .cursor/mcp.json are NOT staged
git commit -m "Initial release: Stability Studio MCP for ComfyUI and Stability Matrix"
git branch -M main
git remote add origin https://github.com/Jamescd1980/stability-studio.git
git push -u origin main
```

## Zip / handoff (no git)

```powershell
python stability-studio-mcp/scripts/build_handoff_zip.py
# Writes studio-agent.zip at repo root (~0.3 MB, no secrets, no dev/ or legacy/)
```

Recipient steps: `install.ps1` → copy `config.yaml.example` → edit paths → copy workflow JSON → install Wan assets per `WAN-ASSETS.md`.

## What gets published

| Included | Excluded (gitignore or zip skip) |
| --- | --- |
| MCP server source | `stability-studio-mcp/config.yaml` |
| `config.yaml.example`, `catalog.yaml` | `stability-studio-mcp/outputs/*` except placeholders |
| Docs, `config-examples/`, `.cursor/rules/` | `outputs/local/`, `__pycache__/`, media files |
| `stability-studio-mcp/workflows/*.json` | `.cursor/mcp.json` (use `.example`) |
| `scripts/remote-laptop/`, `handoff/remote-laptop/` | `config.generated.yaml`, `.handoff-extract/` |
| `packaging/laptop-remote/INSTALL.ps1` | Personal `jan-config/` with absolute paths |
| | `wan_video_loras_local.py`, `studio-agent.zip` |

## Scripts layout

| Path | Ship? |
|------|-------|
| `scripts/download_wan_assets.py`, `check_asset_updates.py` | Yes |
| `scripts/storyboard/generate_storyboard.py` | Yes |
| `scripts/experiments/kitsune_full_test.py` | Yes (example) |
| `scripts/dev/` | No — Invoke migration, local probes |
| `scripts/storyboard/legacy/` | No — deprecated per-scene runners |

## Cursor cloud agents

Generation requires a **local ComfyUI stack**. Cloud agents can contribute code; they cannot run `generate_image` on GitHub-hosted runners without a GPU ComfyUI deployment.

## Release

- **Version:** `1.0.0-beta` — see [RELEASE.md](RELEASE.md) and [CHANGELOG.md](CHANGELOG.md)
- Tag: `v1.0.0-beta`
- Pre-zip: `python stability-studio-mcp/scripts/clean_outputs.py`

## Validated stack (June 2026)

| Feature | Path |
|---------|------|
| Images | `generate_image` + catalog styles |
| T2V | `workflow_id=t2v`, Wan 2.1 1.3B — 81 frames @ 16 fps on 16 GB |
| I2V draft | `i2v_5b`, `image_path` — 65 frames max on 16 GB |
| Hero I2V | `generate_video_hero` — 49f @ 832×480 on 16 GB |
| Storyboard | `scripts/storyboard/generate_storyboard.py` |

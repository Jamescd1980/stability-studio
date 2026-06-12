# Windows paths — Stability Studio

Avoid path-related failures on Windows setups.

## Do

- Keep Stability Matrix under a **short local path**, e.g. `D:\StabilityMatrix-win-x64\`
- Use **absolute paths** in `config.yaml` and MCP tool calls (`image_path`, `video_path`)
- Copy hero stills into `stability-studio-mcp/outputs/` or ComfyUI `input/` when paths get long
- Set `outputs.delivery` to a **project root** (not a flat dump folder), e.g. `C:\Users\<you>\Desktop\New Images\Story Board Project Bata`
- Wan2GP / MOSS raw saves go to **`delivery/temp/`**; promote approved files to `clips/`, `images/`, `audio/`
- Control maps (canny, lineart, openpose) belong in **`delivery/assets/`**, not beside hero stills
- JSON run logs belong in **`delivery/logs/`** (MCP `outputs/` keeps setup JSON + `_run_*.py` scripts only)

## Avoid

| Risk | Why |
|------|-----|
| **OneDrive-synced** project folders | Locked files, long paths, Cursor asset copies under `AppData\...\workspaceStorage\...` |
| Paths with **`&`, `#`, unicode spaces** | ComfyUI upload and ffmpeg mux edge cases |
| Mixing **Roaming** Cursor asset paths in production scripts | Fine for chat uploads; copy to `outputs/` for repeatable pipelines |
| **Two ComfyUI instances** on port 8188 | DB lock, random connection drops |

## Canonical paths (this machine)

Configured via `config.yaml` (not committed):

| Role | Typical location |
|------|------------------|
| Stability Matrix data | `D:\StabilityMatrix-win-x64\Data\` |
| ComfyUI | `...\Packages\ComfyUI\` |
| Wan2GP | `...\Packages\Wan2GP\` |
| MCP outputs | `studio-agent\stability-studio-mcp\outputs\` |
| Delivery project | `Desktop\New Images\<Project>\` with `temp/`, `images/`, `assets/`, `clips/`, `audio/`, `logs/`, `final/` |

Call **`list_media_paths`** or read `get_generation_context.media_paths` for live values.

## Wan2GP CLI

`wgp.py --process settings.json` resolves `image_start` relative to the **Wan2GP package folder** unless you pass an absolute path. Prefer absolute paths in generated settings JSON.

## Cursor chat image uploads

Images attached in chat land under:

`C:\Users\<you>\.cursor\projects\<workspace>\assets\`

These work with MCP but are awkward for scripts — copy to `outputs/` or ComfyUI `input/` for kitsune/Wan2GP pipelines.

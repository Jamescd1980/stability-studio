# Blender MCP (GENERATION_HOST RTX 5090)

Control Blender on **GENERATION_HOST** from Cursor via [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp). Exports land on the Game drive for Stability Studio pose-guided stills.

**Lessons / pitfalls:** [LESSONS-BLENDER-MCP.md](LESSONS-BLENDER-MCP.md) (tool-count note, GPU exclusivity, bind patch).

## Architecture

| Piece | Where |
|-------|--------|
| Blender 4.5 + addon | GENERATION_HOST `<MODELS_MOUNT>/apps/blender` |
| MCP socket | `GENERATION_HOST:9876` (binds `0.0.0.0`) |
| Cursor bridge | Windows `uvx blender-mcp` with `BLENDER_HOST=GENERATION_HOST` |
| Assets | `<MODELS_MOUNT>/GenerationHost Images and Videos/assets/blender/{pose,depth,previz}/` |

**GPU exclusivity:** Do not run heavy Cycles/EEVEE renders while ComfyUI Wan jobs use the 5090. Stop Comfy first (`sudo systemctl stop comfyui` or `~/bin/gpu_backend.sh`), then Blender; reverse before `generate_image` / `generate_video`.

## Start Blender MCP on GENERATION_HOST

```bash
ssh GENERATION_HOST
# optional: free GPU
sudo systemctl stop comfyui
~/bin/generation-host_start_blender_mcp.sh
ss -ltn | grep 9876
tail -f /tmp/blender-mcp/blender.log
```

GUI alternative: `~/bin/start_blender_mcp.sh` then N-panel → **BlenderMCP** → **Connect to MCP server**.

## Cursor

Project [`.cursor/mcp.json`](.cursor/mcp.json) includes the `blender` server. After editing MCP config, **reload MCP / restart Cursor**.

Only one Blender MCP client at a time.

## Smoke

1. Blender listening on `:9876`
2. In Cursor: ask Blender MCP to get scene info or create a cube
3. Export pose PNGs to `assets/blender/pose/` then Stability Studio `generate_image_pose_guided(..., pose_image_path=..., preprocess_pose=false)`

## Paths

| Item | Path |
|------|------|
| Blender binary | `<MODELS_MOUNT>/apps/blender/blender` → `~/bin/blender` |
| Addon | `~/.config/blender/4.5/scripts/addons/blender_mcp_addon.py` |
| Start (xvfb) | `~/bin/generation-host_start_blender_mcp.sh` |
| Start (GUI) | `~/bin/start_blender_mcp.sh` |
| Windows delivery | `D:\GenerationHost Images and Videos\assets\blender\` |

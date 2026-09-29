# Lessons learned — Blender MCP

Updated **2026-08-05**. Blender runs on **LinuxBox RTX 5090**; Cursor on Windows talks over LAN.

## Verdict

Blender MCP is a **separate MCP server** (`uvx blender-mcp`) plus a thin Stability Studio bridge (`get_blender_workflow_playbook`, `register_blender_control_maps`). It does **not** replace pose ControlNet — it feeds better pose/depth maps into the existing `generate_image_pose_guided` path.

## Tool count (Cursor UI)

Cursor’s MCP panel **sums every enabled server**. Example house setup:

| Server | Approx tools | Role |
|--------|-------------:|------|
| **stability-studio** | **~123** | Images, video, audio, storyboard, Forge, Kokoro, … |
| **blender** | dozens | Scene edit, materials, screenshots, … |
| **cursor-app-control** | few | IDE control |

Seeing **123** on Stability Studio alone is expected after Hunyuan / Blender-bridge / NSFW / polish tools landed (was **91** in mid-July). Prefer playbooks (`get_generation_context`, `get_blender_workflow_playbook`) over browsing the full list.

## What worked

| Step | Lesson |
|------|--------|
| Blender on Game drive | `/mnt/game/apps/blender` — not on the tiny OS disk. |
| Addon bind `0.0.0.0:9876` | Default localhost-only bind blocks Windows Cursor. Patch once: `scripts/patch_blender_mcp_bind.py`. |
| Headless start | `~/bin/comfybox_start_blender_mcp.sh` (xvfb). GUI: `~/bin/start_blender_mcp.sh`. |
| Windows `uv` / `uvx` | Install via **winget** (`uv` 0.12.x). Early PowerShell install scripts hung. |
| Cursor env | `BLENDER_HOST=<LinuxBox LAN IP>`, `BLENDER_PORT=9876`, `DISABLE_TELEMETRY=true`. Reload MCP after edit. |
| GPU exclusivity | `gpu_backend.sh blender` stops Comfy before heavy Blender; `comfy` before Wan/stills. |
| Export layout | Pose/depth/previz under `…/assets/blender/{pose,depth,previz}/` then SMB to Windows delivery. |

## Pitfalls

1. **Two clients on :9876** — only one Cursor/Blender-MCP client at a time.
2. **Firewall** — open TCP **9876** on LinuxBox if LAN clients cannot connect.
3. **Phase gaps** — storyboard `needs_pose` queue wiring and depth/previz E2E still open; do not claim full combat pipeline until those land.
4. **Do not commit** live `.cursor/mcp.json` (gitignored). Ship **placeholders** in `config-examples/` and `.cursor/mcp.json.example`.

## Agent path (pose → still)

1. `check_gpu_backend` / free Comfy if needed → start Blender MCP.
2. Blender MCP: pose / export PNG.
3. Switch backend to Comfy.
4. Stability Studio: `register_blender_control_maps` (optional) → `generate_image_pose_guided(..., preprocess_pose=false)`.

Playbook JSON: `get_blender_workflow_playbook()`.

## Related

- [LESSONS-SET-FILL.md](LESSONS-SET-FILL.md) — casting couch BG lock, Darkness mesh turnaround, body prompt rule (2026-08-06)
- [BLENDER-MCP.md](BLENDER-MCP.md) — install / start / paths
- [POSE-CONTROL.md](POSE-CONTROL.md) — ControlNet still path
- [LESSONS-COMFYBOX-CUDA.md](LESSONS-COMFYBOX-CUDA.md) — same GPU stack
- [ACTION-COMBAT.md](ACTION-COMBAT.md) — combat stills (pose-first)

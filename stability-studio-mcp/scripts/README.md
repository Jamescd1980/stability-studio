# Scripts layout

| Folder | Purpose |
|--------|---------|
| **`nsfw/`** | Explicit kits, bj_*, sex_scenes, cum/penis/orgasm downloads, NSFW polish. Scrub this folder for a clean export. |
| **`general/`** | Style recreation, Wan asset downloads, storyboard helpers, smokes that are not cast-sex kits. |
| **`storyboard/`** | Storyboard splice / sheet tools (shared). |
| **`experiments/`** | Ad-hoc batch experiments. |
| **`_bootstrap.py`** | Shared path bootstrap for runners. |

**Rules**

- New explicit runners go in `nsfw/` only.
- Private repo includes both `nsfw/` and `general/`.
- Public may include NSFW **workflows/scripts**; never commit generated NSFW images/videos.
- Windows MCP is source of truth; sync to ComfyBox with `scripts/sync_mcp_to_comfybox.ps1` at repo root `D:\studio-agent\scripts\`.

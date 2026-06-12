# Local experiment scripts

One-off batch tests and character pipelines. Not used by the MCP server.

- Require `config.yaml` and a running ComfyUI instance.
- Paths are often machine-specific — edit argparse defaults before running.
- Prefer MCP tools (`edit_image`, `generate_image`, `generate_video`) for agent workflows.

Reusable maintenance CLIs live in the parent `scripts/` folder (`download_wan_assets.py`, etc.).

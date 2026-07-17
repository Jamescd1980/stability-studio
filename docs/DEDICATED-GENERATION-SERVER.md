# Dedicated generation server (branch plan)

This document lives on branch **`dedicated-generation-server`**. Goal: stop treating “everything on one PC” as the only layout.

## Roles

| Role | Runs | Repo / config |
|------|------|----------------|
| **Client** | Cursor, Jan, MCP server process, project folders | `stability-studio` (scrubbed) + local `config.yaml` |
| **Generation host** | ComfyUI, Forge, Kokoro, models, GPU | Machine secrets + [Private-Studio](https://github.com/Jamescd1980/Private-Studio) `stability-studio` branch |

## Rules

1. Public hub: placeholders only (`GENERATION_HOST`, `http://GENERATION_HOST:8188`).
2. Private hub: real LAN IPs, SSH host aliases, book paths, edge devices (Myra, etc.).
3. Client `config.yaml` / `.cursor/mcp.json` point at the generation host; both stay gitignored.
4. GPU exclusivity (Comfy vs Forge vs Wan2GP) stays on the generation host.

## Migration checklist

- [ ] Client MCP uses remote `comfyui.url` (not only `127.0.0.1`)
- [ ] `comfy_remote_models` readiness path verified from client
- [ ] Forge switch uses `forge.ssh_host` from private config
- [ ] Kokoro URL on generation host; client TTS tools use HTTP only
- [ ] Delivery folders: client-local vs SMB/share documented in Private-Studio
- [ ] Public `stability-studio` CI/docs never mention real hostnames

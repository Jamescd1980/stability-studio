# Jan MCP merge notes (laptop)

Merge `jan-mcp-stability-studio.json.template` into Jan MCP config (`Settings → MCP Servers` or `mcp_config.json`).

## Required MCP server entry

```json
"stability-studio": {
  "active": true,
  "command": "<PYTHON_EXE>",
  "args": ["<PROJECT_ROOT>/stability-studio-mcp/server.py"],
  "env": { "PYTHONUNBUFFERED": "1" },
  "type": "stdio"
}
```

## Required global settings

`generate_image` exceeds 30s. In the same `mcp_config.json`:

```json
"mcpSettings": {
  "toolCallTimeoutSeconds": 600,
  "enableSmartToolRouting": true
}
```

Match `comfyui.timeout_seconds: 600` in laptop `stability-studio-mcp/config.yaml`.

## Assistant instructions

Paste `jan-assistant-instructions.md` into Studio Copilot after filling `<DESKTOP_HOSTNAME>` and `<DESKTOP_LAN_IP>`.

## Desktop Jan

Set `"active": false` for `stability-studio` on the desktop if only the laptop should drive generation.

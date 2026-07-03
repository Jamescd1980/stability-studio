# Jan — file read/write options

Jan does **not** read or write project files by default. Your `mcp_config.json` has **filesystem MCP disabled** (`"active": false`) with a placeholder path.

## What Jan can do today (no filesystem MCP)

| Capability | How |
|------------|-----|
| **Vision** | Attach images in chat (base64 — not project paths) |
| **Generate images** | `stability-studio` → `generate_image` → saves to MCP `outputs/` or delivery folder |
| **Project logs** | `stability-studio` → `get_project_context`, `log_image_prompt`, `list_image_prompt_log` |
| **Read spreadsheet** | Not directly — use Cursor/OI, or enable filesystem MCP below |

**Recommended:** Use **Stability Studio MCP** as Jan’s “file API” for the Bata project. It writes to paths under `outputs.delivery` without giving Jan access to your whole drive.

## Image prompt log (new)

| File | Purpose |
|------|---------|
| `logs/prompt_log.jsonl` | Every prompt brainstorm + every `generate_image` run |

| MCP tool | When |
|----------|------|
| `log_image_prompt` | **Prompt Lab** — after each Platform/Positive/Negative reply |
| `list_image_prompt_log` | “What prompt did we use for scene X?” |
| `generate_image` | Auto-appends to prompt log on success |

Example entry:
```json
{"ts":"2026-06-14T...","agent":"jan","kind":"prompt_only","platform":"illustrious","style":"ilustmix","prompt_positive":"masterpiece, ...","scene_id":"ch01_003_dialogue","status":"prompt_only"}
```

## Optional: enable filesystem MCP (read CSV in Jan)

Edit `D:\Jan\data\mcp_config.json` — set filesystem **active** and scope folders only:

```json
"filesystem": {
  "active": true,
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "C:/Users/You/Projects/YourStoryboardProject",
    "D:/studio-agent/stability-studio-mcp/outputs"
  ],
  "env": {}
}
```

Restart Jan. Jan can then read `storyboard/ch01_storyboard.csv` and list `images/` — still **cannot** call `generate_image` from Prompt Lab if instructions forbid it.

**Security:** Only add folders you trust; the model can read everything under those roots.

## Division of labor

| Agent | Files | Prompts | GPU |
|-------|-------|---------|-----|
| **Jan Prompt Lab** | `log_image_prompt` only | Write + log | No |
| **Jan Production** | via MCP | Read log, generate | Yes (unload Jan first) |
| **Cursor / OI** | Full repo + Bata folder | Edit CSV, logs | Via MCP |

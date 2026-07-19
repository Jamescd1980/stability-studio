# Setup / restore (download and go)

Private clone recovery after a wipe. **No API keys are stored in git.**

## 1. Clone

```bash
git clone https://github.com/Jamescd1980/Private-Studio.git studio-agent
cd studio-agent
```

Public hub (scrubbed): `https://github.com/Jamescd1980/stability-studio.git` — do not treat it as a full restore of private kits.

## 2. MCP config (secrets stay local)

```powershell
copy stability-studio-mcp\config.yaml.example stability-studio-mcp\config.yaml
# Edit paths + paste Civitai key into config.yaml OR set env CIVITAI_API_TOKEN
```

`stability-studio-mcp/config.yaml` is gitignored. Never commit it.

## 3. Python deps

```powershell
cd stability-studio-mcp
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

Optional polish venv: see `config.yaml.example` → `local_post`.

## 4. Cursor / Jan MCP

- Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` and point at your Python.
- Jan: point stability-studio at `stability-studio-mcp/server.py`.

## 5. Ollama brains (weights via pull, not git)

| Tag | Host | Modelfile |
|-----|------|-----------|
| `myra-gofor` | Pi | `ollama/myra-gofor/` |
| `nari` / `nari-prompt` | ComfyBox | `ollama/nari/` |
| `orla` | Windows | `ollama/orla/` |

```powershell
# Example on Windows for Orla
ollama pull huihui_ai/qwen2.5-abliterate:7b-instruct
ollama create orla -f ollama\orla\Modelfile
py -3 ollama\orla\orla_tools.py
```

## 6. Sync MCP mirror to ComfyBox

Windows is source of truth:

```powershell
py -3 scripts\sync_mcp_to_comfybox.py
```

Creates `/mnt/game/studio-agent/stability-studio-mcp/SYNCED_FROM_WINDOWS.txt`.  
Do **not** edit catalog only on ComfyBox.

## 7. Delivery folder

Create / use `D:\ComfyBox Images and Videos` with `Images\` and `Video\`.  
JSON/logs may stay under `stability-studio-mcp/outputs/`; media belongs in ComfyBox delivery.

## 8. Myra (Pi)

```bash
# From Windows after editing handoff/myra-patches:
scp handoff/myra-patches/*.py myra:~/studio-edge/studio_edge/
scp handoff/myra-patches/config.yaml myra:~/studio-edge/config.yaml
scp -r handoff/myra-patches/cast myra:~/studio-edge/studio_edge/cast
ssh myra 'bash ~/studio-edge/restart_edge.sh'
```

Export cast lists after catalog changes:

```powershell
py -3 stability-studio-mcp\scripts\general\export_cast_lists.py
```

## 9. Checklist after restore

- [ ] `config.yaml` present locally with empty→filled keys (not in git)
- [ ] ComfyUI reachable (`http://YOUR_COMFY:8188/system_stats`)
- [ ] Orla tools `:11436/status`
- [ ] Myra log shows `Studio Edge ready`
- [ ] `scripts/nsfw/` present if you need private kits
- [ ] Cast lists under `handoff/myra-patches/cast/`

## Script folders

See [`stability-studio-mcp/scripts/README.md`](stability-studio-mcp/scripts/README.md) — NSFW kits live under `scripts/nsfw/` for easy scrubbing.

# Orla (Windows main-rig CPU)

**Host:** Windows / main rig (7900X + RTX 5060 Ti) — Ollama on **CPU**  
**Role:** Polish + display — open stills/clips, upscale, RIFE/interp, ffmpeg  
**Not Myra** (Pi gofor). **Not Nari** (ComfyBox create/refine/clip).

| Tag | Use |
|-----|-----|
| `orla` | Polish/display language brain for Myra `ask_orla` |

**Base:** `huihui_ai/qwen2.5-abliterate:7b-instruct`

## Setup

```powershell
cd D:\studio-agent\ollama\orla
# Expose on LAN so the Pi can reach Orla
$env:OLLAMA_HOST = "0.0.0.0:11434"
# Prefer CPU for the chat brain (leave 5060 Ti for polish GPU tools later)
$env:OLLAMA_NUM_GPU = "0"
ollama serve
# other terminal:
ollama pull huihui_ai/qwen2.5-abliterate:7b-instruct
ollama create orla -f Modelfile
```

LAN from Pi (set in Myra `config.yaml` → `orla.base_url`):

`http://<WINDOWS_LAN_IP>:11434/v1`

## Companion tools

`orla_tools.py` — tiny HTTP helper for open/display (port **11436**).  
Start with `start_orla.ps1`.

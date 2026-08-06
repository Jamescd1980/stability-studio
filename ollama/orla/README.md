# Orla (Windows main-rig)

**Host:** Windows / main rig (7900X + RTX 5060 Ti)  
**Role:** Polish + display + **still VLM QA**  
**Not Myra** (Pi gofor). **Not Nari / Cursor gen** (ComfyBox create — user trusts Cursor agent for gens).

| Tag | Use | Device |
|-----|-----|--------|
| `orla` | Polish/display language brain for Myra `ask_orla` | CPU/GPU OK |
| `orla-vl` | Still checklist reviewer (Qwen3-VL 8B) | **5060 Ti GPU** |

**Text base:** `huihui_ai/qwen2.5-abliterate:7b-instruct`  
**VLM base:** `qwen3-vl:8b` → tag `orla-vl`  
**Fallback VLM:** `qwen2.5vl:7b` (already pulled; set `ORLA_VLM_MODEL`)

Why Qwen3-VL 8B: strongest practical Ollama multimodal that fits 16 GB with headroom. 32B-class VLMs need ~18–21 GB — too tight on the 5060 Ti. ComfyUI stays on ComfyBox (`.57`); local GPU is free for Orla VLM.

## Setup / start

```powershell
cd D:\studio-agent\ollama\orla
.\start_orla.ps1
```

Manual:

```powershell
$env:OLLAMA_HOST = "0.0.0.0:11434"
# GPU enabled (do NOT set OLLAMA_NUM_GPU=0 while reviewing stills)
ollama serve
ollama pull qwen3-vl:8b
ollama create orla-vl -f Modelfile.vlm
ollama create orla -f Modelfile
py -3 orla_tools.py
```

**Status**

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
Invoke-RestMethod http://127.0.0.1:11436/status
```

LAN from Pi (`orla.base_url`): `http://192.168.50.42:11434/v1`

## VLM checklist review

Tools sidecar `:11436` action `review_still` scores each still.

**Current pass (anatomy gate):** hard-fail on deformed bodies, melted faces, bad hands, missing/extra limbs, fused extras. Hair / cast / roles / breast scale / pose-act are **advisory only** (soft notes) — do not alone force `overall=fail`. Restart `orla_tools.py` after prompt edits.

Advisory fields still returned for later cast passes:
- Hair color + style / separation / Darkness blonde tint
- Eyes / elf ears / breast scale
- Pose/act + roles
- Lighting / male leak (leak soft unless anatomy also broken)
- `overall`: `pass` | `soft_pass` | `fail` + `short_notes` (anatomy-first)

### Report paths

```
D:\ComfyBox Images and Videos\Images\vlm_reports\<same relative folder>\<stem>.json
D:\ComfyBox Images and Videos\Images\vlm_reports\<same relative folder>\<stem>.md
```

Example:

```
...\Images\scene_match_comfy_v2\FD_facesit_A_fern_on_darkness.png
→ ...\Images\vlm_reports\scene_match_comfy_v2\FD_facesit_A_fern_on_darkness.json
→ ...\Images\vlm_reports\scene_match_comfy_v2\FD_facesit_A_fern_on_darkness.md
```

### Gen agent (Cursor) — call after each still

```powershell
$body = @{
  action = "review_still"
  path = "D:\ComfyBox Images and Videos\Images\story_stills_v1\YOUR.png"
  expected = "Fern facesitting Darkness, 2girls, no male, purple hair on top, blonde below"
  write_report = $true
} | ConvertTo-Json

Invoke-RestMethod http://127.0.0.1:11436/action -Method POST -ContentType "application/json" -Body $body
```

Or curl-style from Python:

```python
import json, urllib.request
payload = {
    "action": "review_still",
    "path": r"D:\ComfyBox Images and Videos\Images\....png",
    "expected": "Beat description + who/act + girls-only or partnered",
    "write_report": True,
}
req = urllib.request.Request(
    "http://127.0.0.1:11436/action",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print(json.load(urllib.request.urlopen(req, timeout=300)))
```

Read `report.overall` / `report.short_notes` before chaining the next beat. Do **not** treat Orla as a generator.

### Auto watcher (as images land)

```powershell
# continuous
py -3 D:\studio-agent\ollama\orla\watch_stills_vlm.py

# one-shot smoke over scene_match + story_stills
py -3 D:\studio-agent\ollama\orla\watch_stills_vlm.py --once --dirs scene_match_comfy_v2 story_stills_v1
```

Default watch roots under `Images\`: `story_stills_v1`, `scene_match_comfy_v2`, `scene_match_comfy`.

## Companion tools

`orla_tools.py` — HTTP helper (port **11436**).

| Action | Purpose |
|--------|---------|
| `status` | Health + `vlm_model` |
| `open` / `display` | Show still/clip |
| `describe_image` | Tags / short caption |
| `review_still` | Checklist JSON + report files |
| `phonetic_rewrite` | Kokoro prep |

## GPU policy

- ComfyBox (`.57`) = ComfyUI / Forge / Wan gens  
- Main rig 5060 Ti = Orla VLM + local polish (RIFE/SeedVR2)  
- If something else needs the 5060 Ti, stop the VLM watcher and unload: `ollama stop orla-vl`

# Nari + nari-prompt (ComfyBox Ollama)

**Host:** `comfybox` / LinuxBox (`192.168.50.57`) — Ryzen 5 8600G + RTX 5090  
**Not Myra.** Myra is the Pi gofor.  
**Not Orla.** Orla is the Windows PC name.

| Tag | Use |
|-----|-----|
| `nari` | Create / Forge refine / Wan clip language + vision brain |
| `nari-prompt` | Eric's Prompt Enhancers (`model_name=nari-prompt`) |

**Base:** Huihui **Qwen3.8-27B abliterated** GGUF `Q4_K` (NSFW-capable).  
File: `/mnt/game/ollama/gguf/Huihui-Qwen3.8-27B-abliterated-Q4_K.gguf` → `ollama create nari` / `nari-prompt`.

**GGUF vs iGPU:** GGUF is the weight format Ollama/llama.cpp use — not “iGPU-only.” On iGPU/Vulkan it is often the *only* practical path; on the **5090** Ollama still loads the same GGUF via **CUDA** (much faster). Prefer **5090 when free**; MCP unloads `nari`/`nari-prompt` before Wan/Forge peaks. Fallback = 760M/CPU if the card is busy.

## Talk paths (Pi)

1. **After Hey Myra:** say `talk to Nari` / `ask Nari …` / `hey nari` — works today.
2. **Direct Hey Nari:** ONNX on Pi (`hey_nari.onnx`).

## Tools (MCP — not Ollama plugins)

Ollama cannot load plugins. Nari gets tools via **Stability Studio MCP** (Cursor / Open Interpreter) or `oi_do.py`:

```bash
py -3 D:\studio-agent\ollama\nari\oi_do.py docs
py -3 D:\studio-agent\ollama\nari\oi_do.py read lessons-wan-i2v
py -3 D:\studio-agent\ollama\nari\oi_do.py who eris
```

- `list_studio_docs` / `read_studio_doc` / `search_studio_docs` — allowlisted `.md`/`.txt`
- `lookup_character_identity` — LoRA vs **baked into waijfu** (Eris Greyrat, …)
- See `NARI-DOC-INDEX.md` and `OLLAMA-TOOLS.md`

## Open Interpreter (Windows → ComfyBox Nari)

```bash
py -3 D:\studio-agent\ollama\nari\configure_open_interpreter.py --default
```

No local Windows LLM for create — OI uses `nari:latest` via nothink proxy `http://192.168.50.57:11435` (forwards to Ollama `:11434` with `think:false`). Game coding = **Coder** on Orla’s 5060 (separate OI profile). Skill: `skills/nari-comfybox/SKILL.md`. Recycle Bin only (`recycle_delivery_media`).

## Eric (Comfy on same box)

```
llm_backend: ollama
api_endpoint: http://127.0.0.1:11434
model_name: nari-prompt
```

## Ops

```bash
ssh comfybox
cd ~/studio-ops/nari
ollama create nari -f Modelfile.nari
ollama create nari-prompt -f Modelfile.nari-prompt
python3 smoke_test.py
```

**Qwen3 thinking:** Ollama defaults thinking on. Clients must send top-level `"think": false` (or `reasoning_effort: "none"` on `/v1`) or content comes back empty. Eric's `Local_LLM_Prompt_Enhancer/llm_backend.py` is patched. Open Interpreter hits **`:11435`** (`ollama_nothink_proxy.py`) which injects both. Start proxy: `~/studio-ops/nari/start_nothink_proxy.sh`.

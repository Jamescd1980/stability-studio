# Nari + nari-prompt (8600G Ollama)

**Host:** `comfybox` / LinuxBox (`192.168.50.57`) — Ryzen 5 8600G  
**Not Myra.** Myra is the Pi gofor (`myra-gofor` on the Pi).  
**Not Orla.** Orla is Windows polish/display (`192.168.50.42`).  
**Not the 7900 XT.** Ollama is forced CPU-only so Comfy/Forge keep the dGPU.

| Tag | Use |
|-----|-----|
| `nari` | Create / Forge refine / Wan clip language brain (Myra `ask_nari`) |
| `nari-prompt` | Eric's Prompt Enhancers (`model_name=nari-prompt`) |

**Base weights:** `huihui_ai/qwen2.5-abliterate:7b-instruct` (not Qwen3).  
Qwen3 defaults to a thinking channel; Eric's nodes don't send `think: false`, so prompts come back empty.

## Eric node settings (Comfy on same box)

```
llm_backend: ollama
api_endpoint: http://127.0.0.1:11434
model_name: nari-prompt
```

From Windows / Pi over LAN: `http://192.168.50.57:11434`

## Ops

```bash
ssh comfybox
sudo systemctl status ollama
ollama list
curl -s http://127.0.0.1:11434/api/tags
```

Recreate tags after editing Modelfiles:

```bash
cd ~/studio-ops/nari   # or sync from D:\studio-agent\ollama\nari
ollama create nari -f Modelfile.nari
ollama create nari-prompt -f Modelfile.nari-prompt
```

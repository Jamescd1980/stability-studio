# Coder on Orla

Local coding agent for **Ren’Py** (Unity later). Runs on Orla’s **5060 Ti** via Ollama (`num_gpu 99`). **GPU-only — no CPU split.**

Create / Wan / Forge / GPU unload-before-diffusion = **Nari on ComfyBox only**. Coder does not share that ritual.

| | |
|--|--|
| Model | `coder:latest` ← **Qwen3-Coder 30B-A3B** MoE (`qwen3-coder:30b`) |
| OI profile | `custom:coder-orla` → **`http://127.0.0.1:11436/v1`** (toolcall proxy) |
| Context | 65k (`num_ctx`) |
| GPU | 5060 Ti full — not CPU, not shared with create |

```powershell
ollama pull qwen3-coder:30b
cd D:\studio-agent\ollama\coder
ollama create coder -f Modelfile
# REQUIRED: tool-call rewrite proxy (OI should use :11436, not raw :11434)
powershell -File D:\studio-agent\ollama\coder\start_toolcall_proxy.ps1
py -3 D:\studio-agent\ollama\coder\configure_open_interpreter.py
```

Legacy `qwen2.5-coder:14b` can stay installed as fallback; Coder no longer uses it.

## Why OI showed JSON and would not run tools

`qwen2.5-coder` (and sometimes Qwen3 via Ollama) can return tool calls as **JSON text in `content`**, not OpenAI `tool_calls`. Interpreter only executes real `tool_calls`.

**Fix:** keep `start_toolcall_proxy.ps1` running (`127.0.0.1:11436` → Ollama `:11434`). Coder profile must use `http://127.0.0.1:11436/v1`. Restart Interpreter after starting the proxy.

## Scope

- Wire `.rpy`, install approved assets per `PATHS.md` / `staging/handoff.md`
- Spellcheck / light copy-edit in `.rpy` OK
- No Wan / Forge / generate_image / Invoke

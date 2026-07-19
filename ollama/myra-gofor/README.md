# myra-gofor (Pi 5)

Small uncensored router for Myra. Lives on the Pi Ollama (`127.0.0.1:11434`).

```bash
# on myra
cd ~/studio-ops/myra-gofor   # or sync from D:\studio-agent\ollama\myra-gofor
ollama pull huihui_ai/qwen2.5-abliterate:3b
ollama create myra-gofor -f Modelfile
ollama list
```

Myra `config.yaml`:

```yaml
local_llm:
  base_url: http://127.0.0.1:11434/v1
  model: myra-gofor
```

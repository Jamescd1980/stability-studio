# Kokoro narrate TTS (audiobook / readback)

CPU text-to-speech on the **generation host** — does **not** need the GPU and does **not** conflict with ComfyUI or Forge.

| Item | Value |
|------|--------|
| Typical service | systemd unit on the generation host (e.g. `narrate-tts.service`) |
| Engine | Kokoro ONNX (`kokoro-onnx`) |
| URL | Set in `config.yaml` → `kokoro.url` (example: `http://GENERATION_HOST:8090`) |
| Health | `GET /health` |
| Voices | `GET /v1/voices` |
| Synth | `POST /v1/tts` JSON `{text, voice, speed, pause_*}` → WAV |

LAN hostnames, book paths, and edge-device wiring stay in the **private** ops repo — not here.

## MCP tools

| Tool | Use |
|------|-----|
| `check_kokoro_backend` | Reachability + voice count (no GPU lock) |
| `list_kokoro_voices` | Voice ids |
| `generate_speech_kokoro` | Short/medium readback clips via MCP |

Config (`config.yaml`):

```yaml
kokoro:
  enabled: true
  url: "http://GENERATION_HOST:8090"
  voice: "am_michael"
  speed: 0.87
  timeout_seconds: 300
```

## Ops (generic)

```bash
ssh GENERATION_HOST 'systemctl status narrate-tts --no-pager'
ssh GENERATION_HOST 'curl -s http://127.0.0.1:8090/health'
```

# Kokoro narrate TTS (audiobook / readback)

CPU text-to-speech — does **not** need the GPU and does **not** conflict with ComfyUI or Forge.

**Owner:** **Orla** (Windows polish brain) — phonetic chapter prep + Kokoro synth.  
**Myra** may still call narrate live for plain “read chapter N” (fast room path).  
**“Rewrite chapter N phonetically for read back”** → Myra `ask_orla` → Orla tools.

**Preferred host (this PC):** Ryzen 9 7900X via `D:\narrate-tts\start_narrate.cmd` → `http://127.0.0.1:8090`  
**Fallback:** comfybox 8600G systemd `narrate-tts` → `http://GENERATION_HOST:8090`

| Item | Value |
|------|--------|
| Engine | Kokoro ONNX (`kokoro-onnx`) |
| URL | Set in `config.yaml` → `kokoro.url` (local: `http://127.0.0.1:8090`) |
| Health | `GET /health` |
| Voices | `GET /v1/voices` |
| Synth | `POST /v1/tts` JSON `{text, voice, speed, pause_*}` → WAV |
| Blends | `voice: "af_nicole:0.70+bf_emma:0.30"` (accent dial) |

LAN hostnames, book paths, and edge-device wiring stay in the **private** ops repo — not here.

## MCP tools

| Tool | Use |
|------|-----|
| `check_kokoro_backend` | Reachability + voice count (no GPU lock) |
| `list_kokoro_voices` | Voice ids |
| `generate_speech_kokoro` | Short/medium readback clips via MCP |
| `rewrite_chapter_phonetic` | Orla prep — phonetic rewrite (+ optional WAV) |

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

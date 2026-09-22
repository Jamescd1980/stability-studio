# Forge stills backend (ADetailer)

Optional Forge WebUI on the **generation host** (default port **7860**). Exclusive with ComfyUI on the same GPU.

## MCP tools

- `check_forge_backend`
- `switch_stills_backend(backend="forge"|"comfy"|"status"|"stop-all")`
- `generate_image_forge`
- `refine_image_forge`

## Config

```yaml
forge:
  enabled: true
  url: "http://GENERATION_HOST:7860"
  ssh_host: "GENERATION_HOST"
  gpu_backend_script: "~/bin/gpu_backend.sh"
```

Typical flow: Comfy `generate_image` → `switch_stills_backend(forge)` → `refine_image_forge` → `switch_stills_backend(comfy)` → `generate_video`.

Machine-specific hostnames and LAN IPs belong in local `config.yaml` / the private ops repo only.

---

## Face AD keepers (2026-08-09 beach photoshoot)

Cross-link: `D:\Bad boy\TheaterJobs\LESSONS_LEARNED.md` → **Beach photoshoot Forge face AD**. Prompt log: `TheaterJobs\logs\prompt_log.jsonl` scene `beach_photoshoot_fern_face`.

### Sources
- Prefer masters from delivery / `Originals\` / approved stills. Legacy **Invoke** trees may still hold gold plates — treat as archive, not the live touch-up path (use **Krita** for hand fixes; Forge/Comfy on GenerationHost for AI refine). Never start from prior Forge `_face_pass` or surgical inpaint dumps.
- Check `invokeai_metadata` before “fixing” earrings — user often already has `ear rings, jewelry` in neg.

### ADetailer settings that worked
- **Skip img2img** + `face_yolov8n` only (body/outfit lock).
- **AD denoise ~0.38** for Fern beach (0.45+ drifted lips/teeth; high denoise deformed chest).
- `mediapipe_face_mesh_eyes_only` **fails on anime** (instant no-op) — do not use.
- Whole-face YOLO rewrites **mouth too** — keep denoise moderate; put lip color in AD positive + pale-lips in neg.

### House eye / lip AD positives
Eyes (swap color):  
`sharp detailed eyes, large expressive eyes, piercing (color) eyes, detailed iris with intricate patterns, glossy highlights, catchlight, reflections in eyes, sharp pupils, black pupil`

Lips/mouth:  
`detailed mouth, realistic lips, well-defined lips, subtle lip texture, natural lip shine, glossy lips, expressive mouth, sharp lip lines, playful smile`

### Eye LoRA
- `Eyes_for_Illustrious_Lora_Perfect_anime_eyes` @ **0.75** + trigger **`perfect eyes`** (also under Invoke `models\…\Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors`).

### Negatives to keep
`tattoo` / under-eye tattoo, `ear rings`/`earrings`/`jewelry`, `snaggle tooth`/`fangs`, `white pupils`/`star pupils`, pale lips, deformed breasts, clothing-change block. No ear/earlobe in positive.

### Anti-patterns
- Pixel ear/pupil surgery and aggressive masked inpaint after a bad Forge pass.
- Treating Forge outputs as originals.
- Batching “just one more surgical fix” instead of re-prompting from a clean master (or hand-fixing in Krita).
- Spinning **local Invoke** for touch-ups while GenerationHost is idle — send AI refine to the 5090; use Krita for paint.

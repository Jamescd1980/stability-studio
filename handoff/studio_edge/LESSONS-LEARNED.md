# Studio Edge / Myra — lessons learned (2026-07-19)

Private-studio session notes for voice image path, gold stills, and NSFW prompting.

## Architecture (keep)

| Role | Box | Job |
|------|-----|-----|
| Myra | Pi 5 | Wake / STT / TTS / room — thin edge only |
| Nari | ComfyBox Ollama | Create / brief / Comfy text expand |
| Orla | Windows Ollama + tools `:11436` | Gallery / ingest / VLM / upload-to-Comfy |
| ComfyUI | ComfyBox `:8188` | Generation |
| VLM | Windows `qwen2.5vl:7b` | See local stills (images live on Windows) |

Do **not** put studio thinking on the Pi. Mic stays on Pi.

## Quality bar

- **Default finish:** `studio_agent_00009` / recreate_003 stack — `waijfu_alpha`, Eyes + LensFlare + ILDetailerV2, `quality_default: gold_standard`.
- **Game stills (tease batch 1):** `…/scene_packs/01_tease_gold` — best still quality.
- **Pose lock (Stage1 only kept):** `01_tease_gold_v2/01_Frieren_Stage1_forge_gold_v2.png` for WAN finger-insert; OpenPose+i2i can beat pose but lose finish.
- **Smoke direction (next):** gold standard, **no** OpenPose/ControlNet — variety + stronger BG control; cast = **Fern** (not Frieren). Scene groups one at a time: tease → cowgirl → …

## Pose / cast-swap

- Soft English “LOCK pose” is a lie — use **OpenPose ControlNet** and/or **img2img**.
- Cast swap needs hard identity: strip old hair/eye colors, identity tags first, bump cast LoRA, slightly softer CN so face can change.
- OpenPose alone can drift NSFW hand placement; OpenPose + mild i2i helps pose but often hurts gold finish.

## NSFW prompting (waijfu_alpha)

Canonical gold examples: `D:\Invoke AI\outputs\images\*.png` (`invokeai_metadata` — **not stripped** on download).

**Layer order:** quality/scene → style (`anime++`) → **`View from mans POV`** (never “camera”) → vulgar action sentence → sex-act tags.

Example: looking back over shoulder, hands and knees, man grabbing hips, `shoving his cock in her pussy`, `doggystyle, vaginal penetration`. Hole swap via act language (`anal sex` vs `vaginal penetration`).

| Prefer | Avoid |
|--------|--------|
| fingering her pussy | gently rubbing her clit |
| dildo + type/color/size | sex toy |
| vibrator = small wired vibe only | vibrator as generic dildo |
| View / man's POV | camera / DSLR (spawns props) |

Rules live in `.cursor/rules/nsfw-sex-prompting.mdc` and `prompt_sex_lexicon.py` (Nari expand + soft→blunt rewrites).

## Ops / pitfalls

- **AMD Ollama bundle** on Windows was CPU-only (no CUDA). Use official `Programs\Ollama` with CUDA; keep AMD path off user PATH.
- **Sidecars:** write to `D:\studio-agent\orla-sidecars\`, not `Images\*.png.json`.
- **Spoken gallery IDs:** parse `studio agent 9` / `00009` from selector (don’t fall through to newest).
- **Naming:** `studio_agent_*` is canonical (not studio_edge).
- Wake models: only `hey_myra` on Pi until `hey_nari` / `hey_orla` are trained.

## Key paths

- Myra patches: `handoff/myra-patches/` → Pi `~/studio-edge/studio_edge/`
- Orla tools: `ollama/orla/orla_tools.py`
- Invoke prompts mine: `scripts/mine_invoke_prompts.py` → `docs/invoke_nsfw_prompt_examples.md`
- Scene packs: `D:\ComfyBox Images and Videos\User Import\Frieren Sex Sceens\_refined\scene_packs\`

## Deploy reminders

```bash
scp handoff/myra-patches/*.py myra:~/studio-edge/studio_edge/
scp handoff/myra-patches/config.yaml myra:~/studio-edge/config.yaml
ssh myra 'bash ~/studio-edge/restart_edge.sh'
# restart Orla tools after orla_tools.py changes
```

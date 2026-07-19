# Lessons learned — Wan I2V (14B / NSFW)

Updated **2026-07-18** after Frieren Tease Stage1 failures and BJ MoE successes.

## Hard rules

1. **`workflow_id=i2v` = Wan 2.2 I2V-A14B MoE HIGH+LOW** (API builder `studio.wan22_i2v_moe`). Not Wan 2.1 single-UNET, not 5B.
2. **`i2v_5b` is draft/SFW.** It is often censored or weak for NSFW — do not use for tease / BJ / sex scenes.
3. **One Comfy job at a time** on ComfyBox. Interleaving 5B + 14B polluted sequential filenames (`studio_agent_NNNN`).
4. **First-frame identity gate** against the source still (MAE / visual check) before declaring a clip good. Filenames lie.
5. **Never prompt female `cum`** — use orgasm / squirting / juices / wetness. Male climax language is separate.
6. **Free VRAM** after heavy runs (`/free` unload_models). If torch still reports ~70% while ROCm is idle, re-check; restart ComfyUI if stuck.

## Why online clips looked 1000× better

| Them | Us (broken path) |
|------|------------------|
| Wan **2.2** HIGH + LOW experts | Wan **2.1** single UNET (`workflow-wan21-i2v-14b-…`) mislabeled as “14B i2v” |
| Dual `KSamplerAdvanced` (structure → refine) | One `KSampler` |
| Lightning/LightX2V **HIGH+LOW** pair | Wrong/unused Wan 2.1 LightX2V; Orgasm **HIGH only** |
| Action LoRAs as **pairs** on matching branches | Stacked onto one model |
| Soft-body from MoE + motion LoRAs | Prompt tags alone |

Face melt and dead soft-body were mostly **architecture**, not “bad prompts.”

## Proven stack (keep it simple)

```
HIGH UNET  + Lightning HIGH (+ optional action HIGH)  → KSamplerAdv 0..switch
LOW UNET   + Lightning LOW  (+ optional action LOW)   → KSamplerAdv switch..end
WanImageToVideo latent bridge; wan_2.1_vae; umt5_xxl
```

- **Default MCP preset:** 12 steps, switch 6, CFG high 3.0 / low 1.5, Lightning 0.7 / 1.0 when installed.
- **Quality preset** (no Lightning): 20 / 10 / CFG 3.5 — matches BJ `run_bj_wan22_loras.py`.
- **How many LoRAs:** Lightning pair + **at most one** action pair (+ optional face_naturalizer on both). Do not dump five singles on one branch.
- **Orgasm:** always `orgasm_i2v_high` **and** `orgasm_i2v_low` (bundle `female_orgasm`). Auto-pair fills the mate if one half is requested.

## Assets (ComfyBox)

Already present:

- `I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors`
- `I2V/Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors`
- `Wan22-I2V-Orgasm-HIGH-14B.safetensors` / `…-LOW-…`
- Oral / deepthroat HIGH+LOW NSFW pairs
- `umt5_xxl_fp8_e4m3fn_scaled.safetensors`, `wan_2.1_vae.safetensors`

Install LightX2V distill if missing:

```bash
python scripts/download_wan22_lightning_loras.py
```

## Ops checklist

1. `check_gpu_backend` / Comfy only (not Forge)
2. `check_wan_assets(workflow_id="i2v")`
3. `generate_video(mode=i2v, workflow_id=i2v, …)` — one job
4. Gate first frame vs source still
5. `/free` or wait for VRAM dump before next heavy run
6. Polish (RIFE / AnimeSharp) on **main rig**, not during ComfyBox generation

## Catalog map

| id | Meaning |
|----|---------|
| `i2v` | Wan 2.2 MoE (correct 14B path) |
| `i2v_wan21_native` | Legacy single-UNET Wan 2.1 JSON |
| `i2v_5b` / `*_painter` | 5B draft / Painter motion |
| `i2v_wrapper` | Old WanVideoWrapper OpenArt graph |

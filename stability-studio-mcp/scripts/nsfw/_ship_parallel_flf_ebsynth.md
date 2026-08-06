# Ship parallel: FLF2V (ComfyBox) + EBSynth (main rig)

Updated **2026-07-31** after `FD_00153_ebsynth_test.mp4` reject.

## Verdict on “EBSynth test”

That clip was **OpenCV static face composite**, not EBSynth. Binary missing → silent fallback → frozen still faces glued on thrusting bodies (trash). Lesson logged in `LESSONS-WAN-I2V.md` § Wild Fern.

## ComfyBox (GPU)

- Prep: `User Import\FLF_WildFern\WF04_flf_{first,last}.png`
- Quality MoE FLF2V, no Lightning, doggy LoRA @0.55
- **Length: 21f (~1.3s) single micro-thrust** — not 49f multi-pump
- Scripts: `_prep_flf_keys_and_run.py`, `_run_flf_fern_strap.py`
- MCP: `generate_video` does **not** expose `flf2v` yet — script path until wired

## Main rig (restore)

```powershell
python scripts\nsfw\_ebsynth_face_restore.py `
  --video "GUIDE.mp4" `
  --key "D:\ComfyBox Images and Videos\User Import\FLF_WildFern\WF04_flf_first.png" `
  --out "OUT.mp4"
```

- Requires `tools\ebsynth\ebsynth.exe` (jamriska win64). **Fails hard** if missing.
- `--allow-opencv-fallback` = throwaway probe only; do not gate/ship.
- PyPI `ebsynth` package is empty — do not pip-install expecting a binary.
- jamriska.cz DNS failed at install time; use GitHub release / mirror / manual zip drop.

## Parallel rule

While ComfyBox gens next short FLF link, main rig may EBSynth-clean the **prior approved** clip — only with real binary.

## Do not

- Run Forge on comfybox during FLF
- Call OpenCV paste an EBSynth result
- Chain or install a failed mid-eye clip

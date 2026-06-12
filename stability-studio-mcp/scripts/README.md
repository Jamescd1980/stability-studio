# Scripts

| Folder / file | Audience |
|---------------|----------|
| `download_wan_assets.py`, `download_wan_video_loras.py`, `check_asset_updates.py` | **Users** — model maintenance |
| `storyboard/generate_storyboard.py` | **Users** — multi-beat storyboard CLI |
| `experiments/kitsune_full_test.py` | **Example** — end-to-end image + draft video smoke test |
| `experiments/` (other) | Optional local batch tools; paths default from `config.yaml` |
| `dev/` | **Dev-only** — Invoke migration, Civitai search, local probes (excluded from handoff zip) |
| `storyboard/legacy/` | Deprecated per-scene runners; use `generate_storyboard.py` instead |

Handoff zip: `python scripts/build_handoff_zip.py` (repo root parent writes `studio-agent.zip`).

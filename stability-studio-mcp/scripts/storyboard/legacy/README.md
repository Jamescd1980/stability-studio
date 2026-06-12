# Legacy per-beat runners

These `_run_rin_*.py` scripts were one-off helpers for the Rin reference storyboard.
Prefer the unified CLI:

```powershell
cd stability-studio-mcp
python scripts/storyboard/generate_storyboard.py plan --script-file beats.txt --title my_scene
python scripts/storyboard/generate_storyboard.py check --project-dir "D:/path/to/project"
python scripts/storyboard/generate_storyboard.py splice --skip-missing
```

Set `outputs.delivery` in `config.yaml` to skip `--project-dir` on every call.

Manifest lives at `<project>/logs/storyboard_manifest.json`. See `examples/rin_manifest.example.json`.

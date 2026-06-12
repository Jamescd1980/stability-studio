# Local run outputs (gitignored)

Machine-specific JSON, logs, media, and one-off scripts belong in **`outputs/local/`** — not the repo root of `outputs/`.

```powershell
cd stability-studio-mcp
python scripts/clean_outputs.py   # moves stray files into outputs/local/
```

## Shipped references (repo)

| Path | Purpose |
|------|---------|
| `scripts/storyboard/generate_storyboard.py` | Storyboard CLI |
| `scripts/storyboard/examples/` | Manifest + layout templates |
| `studio/storyboard_cli.py` | Reusable plan/check/splice module |

## Delivery projects (`outputs.delivery` in config.yaml)

Project media lives under your configured delivery root — see [PATHS.md](../../PATHS.md) and `scripts/storyboard/examples/recommended_project_layout.json`.

Handoff zip includes only this README and `.gitkeep` from `outputs/`.

# Dev-only scripts (not required for MCP users)

Machine-specific migration and inventory tools. **Excluded from `studio-agent.zip`.**

| Script | Purpose |
|--------|---------|
| `migrate_invoke_to_stability_matrix.py` | One-time Invoke → Stability Matrix model copy |
| `prune_and_remove_invoke.py` | Remove Invoke package after migration |
| `inspect_invoke_models.py` | List Invoke DB checkpoints |
| `find_dark_fantasy_loras.py` | Civitai LoRA search helper |
| `verify_nude_capability.py` / `fix_naked_image.py` / `verify_naked_checkpoint.py` | Local checkpoint probes (`--ref` required) |

All paths default from `config.yaml` (`stability_matrix.models`) or `--sm-models` / `--invoke-root` flags.

Do not run on a fresh clone unless you are migrating from InvokeAI.

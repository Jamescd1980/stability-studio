# Bundled ComfyUI workflow JSON

These files are **templates** checked into the repo. ComfyUI loads workflows from **Stability Matrix**, not this folder.

## Install (once per machine)

Copy every `workflow-*.json` here into your Stability Matrix workflows folder:

```powershell
$wf = "<STABILITY_MATRIX_ROOT>\Data\Workflows"
Copy-Item stability-studio-mcp\workflows\workflow-*.json $wf
```

Replace `<STABILITY_MATRIX_ROOT>` with the path from `config.yaml` (`stability_matrix.root`).

| File | Used by |
|------|---------|
| `workflow-wan22-ti2v-5b-v2v-comfyui-native.json` | `v2v_5b` draft video |
| `workflow-moss-*.json` | MOSS audio (`generate_audio`) |

Wan **I2V** / **T2V** graphs usually come from Stability Matrix’s Wan template pack or your own saved graphs — see [WAN-ASSETS.md](../../WAN-ASSETS.md) and `catalog.yaml` `workflow_id` entries.

After copying, restart ComfyUI if it was already running.

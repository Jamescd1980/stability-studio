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
| `workflow-wan22-i2v-a14b-moe-comfyui-native.json` | `i2v` (Wan 2.2 MoE reference; MCP uses API builder) |
| `workflow-wan21-i2v-14b-comfyui-native.json` | `i2v_wan21_native` (legacy) |
| `workflow-wan22-ti2v-5b-i2v-comfyui-native.json` | `i2v_5b` draft |
| `workflow-wan22-ti2v-5b-v2v-comfyui-native.json` | `v2v_5b` draft video |
| `workflow-moss-*.json` | MOSS audio (`generate_audio`) |

See [LESSONS-WAN-I2V.md](../LESSONS-WAN-I2V.md) and `catalog.yaml` `workflow_id` entries.

After copying, restart ComfyUI if it was already running.

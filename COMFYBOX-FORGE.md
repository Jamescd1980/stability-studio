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

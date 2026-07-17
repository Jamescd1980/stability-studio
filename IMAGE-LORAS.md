# Image LoRAs (NSFW / intimacy)

Optional Illustrious/Pony intimacy LoRAs for stills. Not required for draft T2I.

## MCP tools

1. `check_nsfw_image_loras` — see what is installed
2. `list_nsfw_image_loras` — catalog ids
3. `download_nsfw_image_loras` — fetch missing files into Stability Matrix
4. `resolve_nsfw_scene_loras(scene=...)` — pick LoRA stack for a scene → pass `loras=` to `generate_image`

## Typical flow

```
resolve_nsfw_scene_loras(scene="intimate")
generate_image(style="ilustmix", prompt=..., loras=[...])
```

See also `stability-studio-mcp/studio/nsfw_image_loras.py` and `catalog.yaml` NSFW LoRA entries.

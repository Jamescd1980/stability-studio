# Map shared images folder (laptop)

Desktop shares generated images as SMB share **`StudioBata`**.

| Path | Notes |
|------|-------|
| `\\<DESKTOP_LAN_IP>\StudioBata` | **Preferred** (hostname UNC often fails) |
| `\\<DESKTOP_HOSTNAME>\StudioBata` | Fallback |
| `Z:\` | After mapping (use in MCP config) |

## Quick setup

```powershell
cd <PROJECT_ROOT>
.\scripts\remote-laptop\map_studio_share.ps1
```

Or set env and pass desktop IP:

```powershell
$env:STUDIO_DESKTOP_IP = "192.168.x.x"
$env:STUDIO_DESKTOP_HOST = "YOUR-PC-NAME"
.\scripts\remote-laptop\map_studio_share.ps1
```

## Laptop config.yaml

```yaml
outputs:
  delivery: "Z:/"
```

## Manual map (if script fails)

```powershell
net use Z: \\<DESKTOP_LAN_IP>\StudioBata /user:<DESKTOP_HOSTNAME>\<WINDOWS_USER> /persistent:yes
explorer Z:\images
```

## Desktop fix

```powershell
.\scripts\remote-laptop\setup_shared_images_elevated.cmd
```

Both PCs: **Private** network profile, same Wi-Fi.

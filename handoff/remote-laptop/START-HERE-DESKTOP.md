# START HERE — Desktop agent

```powershell
cd <PROJECT_ROOT>
.\scripts\remote-laptop\install_comfyui_lan_launcher.ps1
.\scripts\remote-laptop\setup_shared_images_elevated.cmd
.\scripts\remote-laptop\verify_desktop_handoff.ps1
```

Launch ComfyUI from Stability Matrix. **Do not** add `--listen` in SM Extra Launch Arguments.

Give the laptop operator: `<DESKTOP_LAN_IP>`, hostname, and run `map_studio_share.ps1` on their side.

See `handoff/remote-laptop/GITHUB-HANDOFF.md` before pushing to GitHub.

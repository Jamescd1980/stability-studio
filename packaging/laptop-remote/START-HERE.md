# Remote Image Generation package

One-click laptop setup beside a copy of `studio-agent/` from `studio-agent.zip`.

## Layout

```
packaging/laptop-remote/
  INSTALL.ps1          <- run on laptop
  START-HERE.md
studio-agent/          <- from studio-agent.zip (sibling or parent copy)
```

## Before install

Set desktop constants (or env vars):

```powershell
$env:STUDIO_DESKTOP_HOST = "YOUR-PC-NAME"
$env:STUDIO_DESKTOP_IP   = "192.168.x.x"
```

## Install

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\INSTALL.ps1
```

## Docs

- `handoff/remote-laptop/LAPTOP-CURSOR-SETUP.md`
- `handoff/remote-laptop/LESSONS-LEARNED.md`
- `REMOTE-LAPTOP-SETUP.md` (repo root)

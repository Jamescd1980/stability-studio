# Fallback ComfyUI start with LAN bind (when Stability Matrix is closed)
. (Join-Path $PSScriptRoot "_config.ps1")

$ErrorActionPreference = "Stop"
$SmRoot = Get-StabilityMatrixRoot
$Python = Join-Path $SmRoot "Data\Packages\ComfyUI\venv\Scripts\python.exe"
$ComfyDir = Join-Path $SmRoot "Data\Packages\ComfyUI"
$Port = 8188
$Launcher = Join-Path $ComfyDir "studio_launch.py"
$Entry = if (Test-Path $Launcher) { "studio_launch.py" } else { "main.py" }
$ExtraListen = if ($Entry -eq "main.py") { @("--listen") } else { @() }

if (-not (Test-Path $Python)) { Write-Error "ComfyUI venv not found at $Python" }

Get-NetTCPConnection -LocalPort $Port -State Listen -EA SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -EA SilentlyContinue }
Start-Sleep 2

$env:VHS_USE_IMAGEIO_FFMPEG = "1"
Start-Process $Python -ArgumentList @("-u", $Entry, "--reserve-vram", "0.9", "--use-pytorch-cross-attention", "--enable-manager") + $ExtraListen `
    -WorkingDirectory $ComfyDir -WindowStyle Normal
Write-Host "Started ComfyUI. Prefer launching from Stability Matrix when possible." -ForegroundColor Cyan

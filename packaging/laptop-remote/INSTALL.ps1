# Remote Image Generation - laptop one-click setup
# Run: Set-ExecutionPolicy -Scope Process Bypass; .\INSTALL.ps1
#
# Edit these before running (or set env vars STUDIO_DESKTOP_HOST / STUDIO_DESKTOP_IP):
$DesktopHost = if ($env:STUDIO_DESKTOP_HOST) { $env:STUDIO_DESKTOP_HOST } else { "<DESKTOP_HOSTNAME>" }
$DesktopIp   = if ($env:STUDIO_DESKTOP_IP)   { $env:STUDIO_DESKTOP_IP }   else { "<DESKTOP_LAN_IP>" }

$ErrorActionPreference = "Stop"
$PackageRoot = $PSScriptRoot
$RepoRoot    = Join-Path $PackageRoot "studio-agent"
$McpDir      = Join-Path $RepoRoot "stability-studio-mcp"
$ConfigSrc   = Join-Path $RepoRoot "config-examples\laptop-remote\config.yaml.template"
$ConfigDst   = Join-Path $McpDir "config.yaml"
$ShareIp     = "\\$DesktopIp\StudioBata"

Write-Host ""
Write-Host "=== Remote Image Generation - Laptop Setup ===" -ForegroundColor Cyan

function Find-Python {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    $fromPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($fromPath -and $fromPath -notmatch "WindowsApps") { return $fromPath }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "[!] Python 3.10+ not found. Install from python.org (Add to PATH), then re-run." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Python: $py" -ForegroundColor Green

try {
    Invoke-WebRequest "http://${DesktopIp}:8188/system_stats" -UseBasicParsing -TimeoutSec 10 | Out-Null
    Write-Host "[OK] Desktop ComfyUI reachable" -ForegroundColor Green
} catch {
    Write-Host "[!] Cannot reach http://${DesktopIp}:8188 - fix desktop first" -ForegroundColor Yellow
}

& (Join-Path $RepoRoot "scripts\remote-laptop\map_studio_share.ps1") -DesktopHost $DesktopHost -DesktopIp $DesktopIp

Set-Location $McpDir
& $py -m pip install -r requirements.txt

if (Test-Path $ConfigSrc) {
    $yaml = Get-Content $ConfigSrc -Raw
    $yaml = $yaml.Replace("<DESKTOP_LAN_IP>", $DesktopIp)
    Set-Content $ConfigDst $yaml -Encoding UTF8
    Write-Host "[OK] config.yaml installed" -ForegroundColor Green
}

$janDir = Join-Path $PackageRoot "jan-config"
New-Item -ItemType Directory -Path $janDir -Force | Out-Null
$serverPy = (Join-Path $McpDir "server.py").Replace("\", "/")
@{
    "stability-studio" = @{
        active  = $true
        command = $py
        args    = @($serverPy)
        env     = @{ PYTHONUNBUFFERED = "1" }
        type    = "stdio"
    }
} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $janDir "stability-studio-mcp.json") -Encoding UTF8

Write-Host ""
Write-Host "Jan: merge jan-config\stability-studio-mcp.json; set toolCallTimeoutSeconds=600" -ForegroundColor Cyan
Write-Host "See handoff/remote-laptop/LESSONS-LEARNED.md" -ForegroundColor Cyan

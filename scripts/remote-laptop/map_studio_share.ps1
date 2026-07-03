# Map desktop StudioBata share as Z: (run on LAPTOP)
param(
    [string]$DesktopHost = $env:STUDIO_DESKTOP_HOST,
    [string]$DesktopIp = $env:STUDIO_DESKTOP_IP,
    [string]$ShareName = "StudioBata",
    [string]$DriveLetter = "Z"
)

$ErrorActionPreference = "Stop"
if (-not $DesktopIp) { $DesktopIp = Read-Host "Desktop LAN IP (preferred over hostname)" }
if (-not $DesktopHost) { $DesktopHost = Read-Host "Desktop hostname (for /user: creds)" }

$ShareIp = "\\$DesktopIp\$ShareName"
$ShareUnc = "\\$DesktopHost\$ShareName"

# Prefer IP — hostname UNC often fails from laptop (see LESSONS-LEARNED.md)
$target = if (Test-Path $ShareIp) { $ShareIp } elseif (Test-Path $ShareUnc) { $ShareUnc } else { $null }

if (-not $target) {
    Write-Error "Cannot reach share. On desktop run setup_shared_images_elevated.cmd"
}

net use "${DriveLetter}:" /delete /y 2>$null | Out-Null
$credUser = "${DesktopHost}\$env:USERNAME"
Write-Host "Mapping ${DriveLetter}: -> $target (use /user:$credUser if prompted)" -ForegroundColor Cyan
net use "${DriveLetter}:" $target /user:$credUser /persistent:yes
if ($LASTEXITCODE -ne 0) {
    Write-Host "Retry without embedded user (interactive password)..." -ForegroundColor Yellow
    net use "${DriveLetter}:" $target /persistent:yes
}

Write-Host "[OK] ${DriveLetter}: -> $target" -ForegroundColor Green
Write-Host "Set outputs.delivery: `"Z:/`" in laptop stability-studio-mcp/config.yaml"
Get-ChildItem "${DriveLetter}:\" | Select-Object Name

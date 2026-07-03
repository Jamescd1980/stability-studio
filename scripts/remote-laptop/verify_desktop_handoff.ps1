# Verify desktop remote-laptop handoff
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "_config.ps1")

$ok = $true
function Check([string]$label, [scriptblock]$test) {
    if (& $test) {
        Write-Host "[OK] $label" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $label" -ForegroundColor Red
        $script:ok = $false
    }
}

Write-Host "`n=== Remote laptop — desktop verification ===" -ForegroundColor Cyan
$ip = Get-DesktopLanIp
$port = 8188

Check "ComfyUI LAN 0.0.0.0:$port" { netstat -ano | Select-String "0\.0\.0\.0:$port\s" }
Check "ComfyUI HTTP" {
    try { (Invoke-WebRequest "http://${ip}:$port/system_stats" -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200 }
    catch { $false }
}
Check "SMB share StudioBata" { net share StudioBata 2>&1 | Select-String StudioBata }
Check "studio_launch.py installed" {
    Test-Path (Join-Path (Get-StabilityMatrixRoot) "Data\Packages\ComfyUI\studio_launch.py")
}
$delivery = Get-DesktopDeliveryPath
if ($delivery) {
    Check "delivery images/" { Test-Path (Join-Path $delivery "images") }
}

Write-Host ""
if ($script:ok) { Write-Host "Ready for laptop Z: mapping." -ForegroundColor Green }
else { Write-Host "Run install_comfyui_lan_launcher.ps1 + setup_shared_images_elevated.cmd" -ForegroundColor Yellow }
exit $(if ($script:ok) { 0 } else { 1 })

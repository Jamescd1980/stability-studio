# Install studio_launch.py into ComfyUI package (Stability Matrix LAN bind).
# Close Stability Matrix first.
#   cd <PROJECT_ROOT>
#   .\scripts\remote-laptop\install_comfyui_lan_launcher.ps1

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_config.ps1")

$RepoLauncher = Join-Path $PSScriptRoot "studio_launch.py"
$SmRoot = Get-StabilityMatrixRoot
$ComfyDir = Join-Path $SmRoot "Data\Packages\ComfyUI"
$DestLauncher = Join-Path $ComfyDir "studio_launch.py"
$SmSettings = Join-Path $SmRoot "Data\settings.json"
$PackageId = "b4455ed1-4f3b-4303-a6e2-0708116f8cfe"

if (-not (Test-Path $RepoLauncher)) { Write-Error "Missing $RepoLauncher" }
if (-not (Test-Path $ComfyDir)) { Write-Error "ComfyUI package not found at $ComfyDir" }

Copy-Item $RepoLauncher $DestLauncher -Force
Write-Host "[OK] Installed $DestLauncher" -ForegroundColor Green

$json = Get-Content $SmSettings -Raw | ConvertFrom-Json
$comfy = $json.InstalledPackages | Where-Object { $_.Id -eq $PackageId } | Select-Object -First 1
if (-not $comfy) { Write-Error "ComfyUI package not found in settings.json" }

$comfy.LaunchCommand = "studio_launch.py"
Write-Host "[OK] LaunchCommand -> studio_launch.py" -ForegroundColor Green

$badNames = @("--listen", "--port", "")
$cleaned = @()
foreach ($arg in $comfy.LaunchArgs) {
    $drop = $false
    if ($arg.Name -in $badNames) { $drop = $true }
    if ($arg.OptionValue -match '^\s*--\s*listen\s*$') { $drop = $true }
    if (-not $drop) { $cleaned += $arg }
}
if ($cleaned.Count -ne $comfy.LaunchArgs.Count) {
    Write-Host "[OK] Removed broken --listen / '-- listen' launch args" -ForegroundColor Green
}
$comfy.LaunchArgs = @($cleaned)

$json | ConvertTo-Json -Depth 20 | Set-Content $SmSettings -Encoding UTF8

Write-Host ""
Write-Host "Do NOT add --listen in SM Extra Launch Arguments (causes '-- listen' typo)." -ForegroundColor Yellow
Write-Host "Launch ComfyUI from Stability Matrix. Verify: netstat -ano | findstr :8188" -ForegroundColor Cyan

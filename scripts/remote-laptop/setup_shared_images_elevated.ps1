# Admin-only: SMB share + file-sharing firewall. Run setup_shared_images_elevated.cmd

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_config.ps1")

$DeliveryPath = Get-DesktopDeliveryPath
if (-not $DeliveryPath) {
    Write-Error "Set outputs.delivery in stability-studio-mcp/config.yaml first, or pass -DeliveryPath"
}
$ShareName = "StudioBata"
$ComputerName = $env:COMPUTERNAME
$DesktopUser = "$ComputerName\$env:USERNAME"

if (-not (Test-Path $DeliveryPath)) {
    New-Item -ItemType Directory -Path $DeliveryPath -Force | Out-Null
}

$subdirs = @(
    "source", "images", "images\chain", "assets", "clips", "audio",
    "temp", "logs", "final", "rejected"
)
foreach ($rel in $subdirs) {
    New-Item -ItemType Directory -Path (Join-Path $DeliveryPath $rel) -Force | Out-Null
}

icacls $DeliveryPath /inheritance:e | Out-Null
icacls $DeliveryPath /grant "CREATOR OWNER:(OI)(CI)(F)" | Out-Null
icacls $DeliveryPath /grant "${DesktopUser}:(OI)(CI)(F)" | Out-Null
icacls $DeliveryPath /grant "NT AUTHORITY\Authenticated Users:(OI)(CI)(M)" | Out-Null
Write-Host "[OK] NTFS permissions on $DeliveryPath" -ForegroundColor Green

if (-not (Get-SmbShare -Name $ShareName -ErrorAction SilentlyContinue)) {
    New-SmbShare -Name $ShareName -Path $DeliveryPath `
        -Description "Stability Studio shared images (laptop)" | Out-Null
}
Grant-SmbShareAccess -Name $ShareName -AccountName "Everyone" -AccessRight Full -Force -ErrorAction SilentlyContinue | Out-Null
Grant-SmbShareAccess -Name $ShareName -AccountName "Authenticated Users" -AccessRight Full -Force -ErrorAction SilentlyContinue | Out-Null
Write-Host "[OK] SMB share \\$ComputerName\$ShareName" -ForegroundColor Green

foreach ($group in @("File and Printer Sharing", "Network Discovery")) {
    Get-NetFirewallRule -DisplayGroup $group -ErrorAction SilentlyContinue |
        Where-Object { $_.Profile -match "Private" } |
        ForEach-Object { if ($_.Enabled -ne "True") { Enable-NetFirewallRule -Name $_.Name | Out-Null } }
}
$smbFwName = "Stability Studio SMB (445)"
if (-not (Get-NetFirewallRule -DisplayName $smbFwName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $smbFwName -Direction Inbound -Protocol TCP `
        -LocalPort 445 -Action Allow -Profile Private | Out-Null
}
Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq "Public" } | ForEach-Object {
    Set-NetConnectionProfile -InterfaceIndex $_.InterfaceIndex -NetworkCategory Private
}

$ip = Get-DesktopLanIp
$readme = @"
# Shared delivery project

Desktop: $ComputerName
UNC: \\$ComputerName\$ShareName
LAN: \\$ip\$ShareName

images/  — finished stills from generate_image
logs/    — prompt_log.jsonl
"@
Set-Content (Join-Path $DeliveryPath "README-SHARED-FOLDER.md") $readme -Encoding UTF8
Write-Host "[OK] Laptop: .\scripts\remote-laptop\map_studio_share.ps1" -ForegroundColor Cyan

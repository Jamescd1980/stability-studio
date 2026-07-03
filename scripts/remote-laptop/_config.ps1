# Shared paths for remote-laptop scripts (desktop).
$script:RemoteLaptopRepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$script:RemoteLaptopMcpConfig = Join-Path $RemoteLaptopRepoRoot "stability-studio-mcp\config.yaml"

function Get-DesktopDeliveryPath {
    param([string]$Default = "")
    if (Test-Path $RemoteLaptopMcpConfig) {
        $raw = Get-Content $RemoteLaptopMcpConfig -Raw
        if ($raw -match '(?m)^\s*delivery:\s*["'']?([^"''#\r\n]+)') {
            $p = $Matches[1].Trim().TrimEnd('/')
            if ($p) { return $p.Replace('/', '\') }
        }
    }
    if ($Default) { return $Default }
    return ""
}

function Get-StabilityMatrixRoot {
    param([string]$Default = "D:\StabilityMatrix-win-x64")
    if (Test-Path $RemoteLaptopMcpConfig) {
        $raw = Get-Content $RemoteLaptopMcpConfig -Raw
        if ($raw -match '(?m)root:\s*["'']?([^"''#\r\n]+)') {
            $p = $Matches[1].Trim()
            if ($p -and $p -notmatch '<') { return $p.Replace('/', '\') }
        }
    }
    return $Default
}

function Get-DesktopLanIp {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -First 1).IPAddress
    return $ip
}

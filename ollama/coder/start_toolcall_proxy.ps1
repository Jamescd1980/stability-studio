# Start Coder tool-call fixup proxy (OI -> :11436 -> Ollama :11434)
$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $dir "ollama_toolcall_proxy.py"
$log = Join-Path $env:TEMP "coder-toolcall-proxy.log"
$errLog = Join-Path $env:TEMP "coder-toolcall-proxy.err.log"

# Already listening?
$listening = Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host "coder toolcall proxy already on :11436 (pid $($listening.OwningProcess))"
    exit 0
}

Start-Process -FilePath "py" -ArgumentList @("-3", $py) -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError $errLog
Start-Sleep -Seconds 1
$ok = Get-NetTCPConnection -LocalPort 11436 -State Listen -ErrorAction SilentlyContinue
if (-not $ok) {
    Write-Host "FAILED to start proxy. Log: $log"
    if (Test-Path $log) { Get-Content $log -Tail 20 }
    if (Test-Path $errLog) { Get-Content $errLog -Tail 20 }
    exit 1
}
Write-Host "coder toolcall proxy listening on 127.0.0.1:11436 (log $log)"

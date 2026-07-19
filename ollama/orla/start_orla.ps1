# Start Orla: Ollama (LAN) + tools sidecar. CPU chat brain.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$cmd = Get-Command ollama -ErrorAction SilentlyContinue
$Ollama = if ($cmd) { $cmd.Source } else { $null }
if (-not $Ollama) {
  $candidates = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:LOCALAPPDATA\AMD\AI_Bundle\Ollama\ollama.exe"
  )
  $Ollama = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Ollama) { throw "ollama.exe not found" }

$env:OLLAMA_HOST = "0.0.0.0:11434"
$env:OLLAMA_NUM_GPU = "0"

# Kill stale tools sidecar on 11436
Get-NetTCPConnection -LocalPort 11436 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host "Starting Orla tools on :11436 ..."
Start-Process -FilePath "py" -ArgumentList @("-3", "$Root\orla_tools.py") -WindowStyle Minimized

# Ensure Ollama is up
try {
  Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 | Out-Null
  Write-Host "Ollama already running on :11434"
} catch {
  Write-Host "Starting Ollama serve (LAN 0.0.0.0:11434, NUM_GPU=0) ..."
  Start-Process -FilePath $Ollama -ArgumentList @("serve") -WindowStyle Minimized
  Start-Sleep -Seconds 3
}

Write-Host "Ensuring base weights + orla tag ..."
& $Ollama pull huihui_ai/qwen2.5-abliterate:7b-instruct
& $Ollama create orla -f "$Root\Modelfile"
& $Ollama list
Write-Host "Orla ready. Pi should use http://192.168.50.42:11434/v1 model=orla"
Write-Host "Tools: http://192.168.50.42:11436/status"

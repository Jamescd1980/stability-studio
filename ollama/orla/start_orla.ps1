# Start Orla: Ollama (LAN + GPU for VLM) + tools sidecar.
# Chat brain `orla` can stay light; VLM `orla-vl` (Qwen3-VL 8B) uses 5060 Ti.
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
# GPU on for VLM (5060 Ti). ComfyUI gens are on ComfyBox (.57) — leave local GPU for Orla.
# To force CPU chat-only again: $env:OLLAMA_NUM_GPU = "0"
Remove-Item Env:OLLAMA_NUM_GPU -ErrorAction SilentlyContinue

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
  Write-Host "Starting Ollama serve (LAN 0.0.0.0:11434, GPU enabled) ..."
  Start-Process -FilePath $Ollama -ArgumentList @("serve") -WindowStyle Minimized
  Start-Sleep -Seconds 3
}

Write-Host "Ensuring text brain + VLM ..."
& $Ollama pull huihui_ai/qwen2.5-abliterate:7b-instruct
& $Ollama create orla -f "$Root\Modelfile"
& $Ollama pull qwen3-vl:8b
& $Ollama create orla-vl -f "$Root\Modelfile.vlm"
# Fallback if someone still asks for the old tag
& $Ollama pull qwen2.5vl:7b
& $Ollama list
Write-Host "Orla ready."
Write-Host "  Chat:  http://192.168.50.42:11434/v1  model=orla"
Write-Host "  VLM:   model=orla-vl  (Qwen3-VL 8B on 5060 Ti)"
Write-Host "  Tools: http://192.168.50.42:11436/status"
Write-Host "  Review: POST /action {`"action`":`"review_still`",`"path`":`"...`",`"expected`":`"...`"}"
Write-Host "  Watcher: py -3 $Root\watch_stills_vlm.py"

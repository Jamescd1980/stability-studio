# Optional: check whether coder is loaded on the 5060.
# There is no Invoke XOR split on Orla — create/diffusion is ComfyBox/Nari only.
param(
    [ValidateSet("status", "unload-coder")]
    [string]$Action = "status"
)

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "ollama not on PATH"
    exit 1
}

switch ($Action) {
    "status" {
        Write-Host "=== Orla / Coder GPU ==="
        Write-Host "Coder = 5060 Ti GPU-only. Create unload-split = ComfyBox/Nari only."
        & $ollama.Source ps
        if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
            nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader
        }
    }
    "unload-coder" {
        & $ollama.Source stop coder 2>$null
        & $ollama.Source stop qwen2.5-coder:14b 2>$null
        & $ollama.Source stop qwen2.5-coder:32b 2>$null
        Write-Host "Coder stopped."
    }
}

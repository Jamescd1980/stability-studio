# Laptop Jan + MCP setup (run on laptop)
$ErrorActionPreference = "Stop"

$RepoRoot = Read-Host "studio-agent path on this laptop"
if (-not (Test-Path $RepoRoot)) { Write-Error "Not found: $RepoRoot" }

$McpDir = Join-Path $RepoRoot "stability-studio-mcp"
$template = Join-Path $RepoRoot "config-examples\laptop-remote\config.yaml.template"
$generated = Join-Path $RepoRoot "config-examples\laptop-remote\config.generated.yaml"
$dst = Join-Path $McpDir "config.yaml"

$py = Read-Host "Python.exe path"
& $py -m pip install -r (Join-Path $McpDir "requirements.txt")

$src = if (Test-Path $generated) { $generated } elseif (Test-Path $template) { $template } else { $null }
if ($src) {
    Copy-Item $src $dst -Force
    Write-Host "[OK] config.yaml from $(Split-Path $src -Leaf) — edit desktop IP if needed" -ForegroundColor Green
}

$ip = Read-Host "Desktop LAN IP for ComfyUI test"
try {
    Invoke-WebRequest "http://${ip}:8188/system_stats" -UseBasicParsing -TimeoutSec 10 | Out-Null
    Write-Host "[OK] ComfyUI reachable" -ForegroundColor Green
} catch {
    Write-Warning "ComfyUI not reachable at $ip"
}

Write-Host "Jan MCP: merge config-examples/laptop-remote/jan-mcp-stability-studio.json.template"
Write-Host "Instructions: config-examples/laptop-remote/jan-assistant-instructions.md"

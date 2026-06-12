# Verify Stability Studio MCP setup for Cursor
$ProjectRoot = $PSScriptRoot
$Server = Join-Path $ProjectRoot "stability-studio-mcp\server.py"
$Config = Join-Path $ProjectRoot "stability-studio-mcp\config.yaml"
$Example = Join-Path $ProjectRoot "stability-studio-mcp\config.yaml.example"
$McpJson = Join-Path $ProjectRoot ".cursor\mcp.json"

Write-Host "Stability Studio — Cursor setup check" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $Server) {
    Write-Host "[OK] MCP server: $Server" -ForegroundColor Green
} else {
    Write-Host "[FAIL] MCP server missing: $Server" -ForegroundColor Red
}

if (Test-Path $McpJson) {
    Write-Host "[OK] Project MCP config: $McpJson" -ForegroundColor Green
} else {
    Write-Host "[MISSING] .cursor/mcp.json — open repo root as Cursor workspace" -ForegroundColor Yellow
}

if (Test-Path $Config) {
    Write-Host "[OK] config.yaml present" -ForegroundColor Green
} elseif (Test-Path $Example) {
    Write-Host "[ACTION] Copy config.yaml.example to config.yaml and edit paths" -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] config.yaml.example missing" -ForegroundColor Red
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Open this folder as the Cursor workspace root: $ProjectRoot"
Write-Host "  2. Settings -> MCP -> confirm stability-studio is enabled"
Write-Host "  3. Launch ComfyUI from Stability Matrix"
Write-Host "  4. For video: set VHS_USE_IMAGEIO_FFMPEG=1 before ComfyUI starts"
Write-Host "  5. Chat: 'Call get_generation_context, then check_backends'"
Write-Host ""
Write-Host "See CURSOR-INTEGRATION.md for cloud vs local agent notes."

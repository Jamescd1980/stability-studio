# Verifies Stability Studio MCP is configured for Open Interpreter
$ProjectRoot = $PSScriptRoot
$Server = Join-Path $ProjectRoot "stability-studio-mcp\server.py"

Write-Host "Open Interpreter MCP setup check" -ForegroundColor Cyan
Write-Host ""

$desktopConfig = "$env:APPDATA\Interpreter\codex-home\config.toml"
$terminalConfig = "$env:USERPROFILE\.openinterpreter\config.toml"

if (Test-Path $desktopConfig) {
    $content = Get-Content $desktopConfig -Raw
    if ($content -match 'stability-studio') {
        Write-Host "[OK] Desktop config: $desktopConfig" -ForegroundColor Green
    } else {
        Write-Host "[MISSING] stability-studio not in desktop config" -ForegroundColor Yellow
        Write-Host "       Merge config-examples\open-interpreter-mcp.toml (set <PROJECT_ROOT>)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] Desktop config not found: $desktopConfig" -ForegroundColor Yellow
}

if (Test-Path $terminalConfig) {
    Write-Host "[OK] Terminal config: $terminalConfig" -ForegroundColor Green
} else {
    Write-Host "[WARN] Terminal config not found" -ForegroundColor Yellow
}

if (Test-Path $Server) {
    Write-Host "[OK] MCP server: $Server" -ForegroundColor Green
} else {
    Write-Host "[FAIL] MCP server missing: $Server" -ForegroundColor Red
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Open Interpreter (fully quit and reopen)"
Write-Host "  2. Launch ComfyUI from Stability Matrix"
Write-Host "  3. Copy config-examples\stability-studio-skill.md to OI skills (LM Studio)"
Write-Host "  4. Merge config-examples\open-interpreter-mcp.toml (tool_timeout_sec=1200 for I2V)"
Write-Host "  5. See OPEN-INTERPRETER-INTEGRATION.md"

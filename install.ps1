# Install Stability Studio MCP dependencies
$ProjectRoot = $PSScriptRoot
Set-Location (Join-Path $ProjectRoot "stability-studio-mcp")

pip install -r requirements.txt

$Config = Join-Path $ProjectRoot "stability-studio-mcp\config.yaml"
$Example = Join-Path $ProjectRoot "stability-studio-mcp\config.yaml.example"
if (-not (Test-Path $Config) -and (Test-Path $Example)) {
    Copy-Item $Example $Config
    Write-Host ""
    Write-Host "Created config.yaml from example — edit stability_matrix paths before use." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Installed. Next steps:"
Write-Host "  1. Tell your AI assistant: 'Help me set up Stability Studio' (reads onboarding/)"
Write-Host "  2. Copy onboarding\config.yaml.template -> stability-studio-mcp\config.yaml and edit paths"
Write-Host "  3. Launch ComfyUI from Stability Matrix"
Write-Host "  4. Cursor: open $ProjectRoot as workspace (uses .cursor/mcp.json)"
Write-Host "  5. Open Interpreter: merge config-examples\open-interpreter-mcp.toml — see OPEN-INTERPRETER-INTEGRATION.md"
Write-Host ""
Write-Host "Onboarding pack: onboarding\README.md"

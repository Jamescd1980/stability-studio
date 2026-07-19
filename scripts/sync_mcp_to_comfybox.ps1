# One-way sync: Windows MCP (source of truth) -> ComfyBox mirror.
$ErrorActionPreference = "Stop"
py -3 "$PSScriptRoot\sync_mcp_to_comfybox.py"
if ($LASTEXITCODE -ne 0) { throw "sync failed: $LASTEXITCODE" }

"""Force-restore Nari (+ Coder) Open Interpreter profiles.

OI often wipes custom local profiles on reload — this rewrites config.toml cleanly.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

NARI_PROFILE = (
    '{ baseURL = "http://192.168.50.57:11435/v1", codexProfileId = "ollama-nari", '
    'id = "custom:nari-comfybox", isBuiltin = false, modelId = "nari:latest", '
    'name = "Nari", provider = "local", providerId = "builtin:local", '
    'useResponsesApi = false, '
    'visionModel = { baseURL = "http://192.168.50.57:11435/v1", '
    'modelId = "nari:latest", provider = "local" }, '
    'wireApi = "chat" }'
)

CODER_PROFILE = (
    '{ baseURL = "http://127.0.0.1:11434/v1", codexProfileId = "ollama-coder", '
    'id = "custom:coder-orla", isBuiltin = false, modelId = "coder:latest", '
    'name = "Coder", provider = "local", providerId = "builtin:local", '
    'useResponsesApi = false, wireApi = "chat" }'
)

HOSTED_SMART = (
    '{ helpDescription = "Routes to the smartest model for the best price.", '
    'id = "onboarding:interpreter-smart", isBuiltin = false, '
    'modelId = "interpreter-smart", name = "Interpreter Smart", '
    'provider = "hosted", providerId = "builtin:hosted" }'
)

HOSTED_FAST = (
    '{ helpDescription = "Routes to the fastest model for the best price.", '
    'id = "onboarding:interpreter-fast", isBuiltin = false, '
    'modelId = "interpreter-fast", name = "Interpreter Fast", '
    'provider = "hosted", providerId = "builtin:hosted" }'
)

TAIL = """
[model_providers.ollama-nari]
base_url = "http://192.168.50.57:11435/v1"
name = "Ollama (Nari / ComfyBox)"
requires_openai_auth = false
wire_api = "chat"

[model_providers.ollama-coder]
base_url = "http://127.0.0.1:11434/v1"
name = "Ollama (Coder / Orla)"
requires_openai_auth = false
wire_api = "chat"

[mcp_servers.onedesk-mcp]
command = "python"
args = ["D:/studio-agent/onedesk-mcp/server.py"]
default_tools_approval_mode = "approve"
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 1200

[mcp_servers.onedesk-mcp.tools.generate_image]
approval_mode = "prompt"

[mcp_servers.onedesk-mcp.tools.generate_video]
approval_mode = "prompt"

[mcp_servers.onedesk-mcp.tools.recycle_delivery_media]
approval_mode = "prompt"

[mcp_servers.onedesk-mcp.tools.check_gpu_backend]
approval_mode = "approve"

[mcp_servers.onedesk-mcp.tools.unload_nari_for_gpu]
approval_mode = "approve"
"""

CLI_CONFIG = """# Open Interpreter CLI — Nari on ComfyBox

model_provider = "ollama-nari"
model = "nari:latest"

[model_providers.ollama-nari]
base_url = "http://192.168.50.57:11435/v1"
name = "Ollama (Nari / ComfyBox)"
requires_openai_auth = false
wire_api = "chat"

[mcp_servers.onedesk-mcp]
command = "python"
args = ["D:/studio-agent/onedesk-mcp/server.py"]
default_tools_approval_mode = "approve"
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 1200
"""


def write_desktop(cfg_path: Path) -> None:
    if cfg_path.exists():
        bak = cfg_path.with_suffix(
            cfg_path.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}"
        )
        shutil.copy2(cfg_path, bak)
        print("backup", bak)

    profiles = ", ".join([NARI_PROFILE, CODER_PROFILE, HOSTED_SMART, HOSTED_FAST])
    body = f"""# Interpreter — restored by studio-agent (Nari + Coder)
# If OI wipes local profiles on launch, re-run: py -3 D:\\studio-agent\\ollama\\nari\\configure_open_interpreter.py

cli_auth_credentials_store = "file"
mcp_oauth_credentials_store = "file"

[windows]
sandbox = "elevated"

[interpreter_app]
default_profile_id = "custom:nari-comfybox"
fast_profile_id = "custom:coder-orla"
profiles = [{profiles}]
storage_version = 1

[interpreter_app.providers]

[interpreter_app.providers."builtin:agent"]
createdAt = 0
id = "builtin:agent"
name = "CLI Agent"
type = "agent"
updatedAt = 0

[interpreter_app.providers."builtin:hosted"]
createdAt = 0
id = "builtin:hosted"
name = "Hosted"
type = "hosted"
updatedAt = 0

[interpreter_app.providers."builtin:local"]
createdAt = 0
id = "builtin:local"
name = "Local (Ollama / LM Studio)"
type = "local"
updatedAt = 0

[interpreter_app.providers."builtin:openai-oauth"]
createdAt = 0
id = "builtin:openai-oauth"
name = "OpenAI (OAuth)"
type = "openai-oauth"
updatedAt = 0

[projects.'D:\\\\Bad boy\\\\TheaterJobs']
trust_level = "trusted"

[projects.'D:\\\\studio-agent']
trust_level = "trusted"
"""
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(body + "\n" + TAIL, encoding="utf-8", newline="\n")
    print("wrote", cfg_path)


def main() -> None:
    desktop = Path.home() / "AppData/Roaming/Interpreter/codex-home/config.toml"
    cli = Path.home() / ".openinterpreter/config.toml"
    skill = (
        Path.home()
        / "AppData/Roaming/Interpreter/codex-home/skills/nari-comfybox/SKILL.md"
    )
    write_desktop(desktop)
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text(CLI_CONFIG, encoding="utf-8", newline="\n")
    print("wrote", cli)
    skill.parent.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).with_name("open_interpreter_SKILL.md")
    if src.is_file():
        skill.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print("wrote", skill)
    text = desktop.read_text(encoding="utf-8")
    assert "custom:nari-comfybox" in text
    assert 'default_profile_id = "custom:nari-comfybox"' in text
    print("OK: Nari is default. Fully quit and reopen Open Interpreter.")


if __name__ == "__main__":
    main()

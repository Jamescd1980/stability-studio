"""Point Open Interpreter desktop + CLI configs at Orla (LLM) + orla-vl (VLM)."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

ORLA_PROFILE = (
    '{ baseURL = "http://127.0.0.1:11434/v1", codexProfileId = "ollama", '
    'id = "custom:orla-ollama", isBuiltin = false, modelId = "orla:latest", '
    'name = "Orla (Ollama LLM)", provider = "local", providerId = "builtin:local", '
    'useResponsesApi = false, '
    'visionModel = { baseURL = "http://127.0.0.1:11434/v1", '
    'modelId = "orla-vl:latest", provider = "local" }, '
    'wireApi = "chat" }'
)

PROVIDER_BLOCK = """
[model_providers.ollama]
base_url = "http://127.0.0.1:11434/v1"
name = "Ollama (Orla)"
requires_openai_auth = false
wire_api = "chat"
"""

CLI_CONFIG = """# Open Interpreter terminal config — Orla (Ollama)
# Desktop app reads: %APPDATA%\\Interpreter\\codex-home\\config.toml

model_provider = "ollama"
model = "orla:latest"

[model_providers.ollama]
base_url = "http://127.0.0.1:11434/v1"
name = "Ollama (Orla)"
requires_openai_auth = false
wire_api = "chat"

# Primary chat / tools brain
# Vision attachments: desktop profile uses visionModel=orla-vl (Qwen3-VL 8B)

[mcp_servers.stability-studio]
command = "python"
args = ["D:/studio-agent/stability-studio-mcp/server.py"]
default_tools_approval_mode = "approve"
enabled = true
startup_timeout_sec = 15
tool_timeout_sec = 1200

[mcp_servers.stability-studio.tools.get_generation_context]
approval_mode = "approve"

[mcp_servers.stability-studio.tools.generate_image]
approval_mode = "prompt"

[mcp_servers.stability-studio.tools.generate_video]
approval_mode = "prompt"
"""


def patch_desktop(cfg_path: Path) -> None:
    bak = cfg_path.with_suffix(cfg_path.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(cfg_path, bak)
    print("backup", bak)

    text = cfg_path.read_text(encoding="utf-8")

    if "custom:orla-ollama" not in text:
        if "profiles = [" not in text:
            raise SystemExit("Could not find profiles = [ in desktop config")
        text = text.replace("profiles = [", "profiles = [" + ORLA_PROFILE + ", ", 1)
        print("inserted Orla profile")
    else:
        # Refresh vision/model ids if profile already exists
        text = re.sub(
            r"\{[^}]*id = \"custom:orla-ollama\"[^}]*\}",
            ORLA_PROFILE,
            text,
            count=1,
        )
        print("refreshed existing Orla profile")

    text = re.sub(
        r'default_profile_id\s*=\s*"[^"]+"',
        'default_profile_id = "custom:orla-ollama"',
        text,
        count=1,
    )
    print("default_profile_id = custom:orla-ollama")

    if "[model_providers.ollama]" not in text:
        if "[mcp_servers.stability-studio]" in text:
            text = text.replace(
                "[mcp_servers.stability-studio]",
                PROVIDER_BLOCK + "\n[mcp_servers.stability-studio]",
            )
        else:
            text += "\n" + PROVIDER_BLOCK
        print("added [model_providers.ollama]")

    text = re.sub(r"(tool_timeout_sec\s*=\s*)\d+", r"\g<1>1200", text)

    cfg_path.write_text(text, encoding="utf-8")
    print("wrote", cfg_path)


def write_cli(cli_path: Path) -> None:
    cli_path.parent.mkdir(parents=True, exist_ok=True)
    if cli_path.exists():
        bak = cli_path.with_suffix(cli_path.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(cli_path, bak)
        print("cli backup", bak)
    cli_path.write_text(CLI_CONFIG, encoding="utf-8")
    print("wrote", cli_path)


def write_skill(skill_path: Path) -> None:
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: "orla-ollama"
description: "Orla local Ollama brain — text/tools LLM plus orla-vl (Qwen3-VL) for images."
---

# Orla (local Ollama)

## Models

| Role | Model | When |
|------|-------|------|
| **LLM (default)** | `orla:latest` | Chat, coding, tools, MCP, planning |
| **VLM** | `orla-vl:latest` | Still QA / attached image analysis (Qwen3-VL 8B) |

The desktop profile wires `visionModel` to the VLM automatically when an image is in the message.
Do **not** load the VLM for plain text tasks.

## Rules

1. Text-only questions → stay on **Orla** (`orla:latest`).
2. Image attached or "what's in this picture / still / screenshot" → use vision path (profile `visionModel`).
3. Image **generation** still goes through `stability-studio__*` MCP (ComfyUI), not the VLM.
4. Never call hosted `interpreter-app` on this local profile.
5. Prefer Stability Studio MCP for generate/edit; Orla VLM only for understanding images.

## Server

Ollama must be running: `http://127.0.0.1:11434`
""",
        encoding="utf-8",
    )
    print("wrote", skill_path)


def main() -> None:
    desktop = Path.home() / "AppData/Roaming/Interpreter/codex-home/config.toml"
    cli = Path.home() / ".openinterpreter/config.toml"
    skill = (
        Path.home()
        / "AppData/Roaming/Interpreter/codex-home/skills/orla-ollama/SKILL.md"
    )
    if not desktop.exists():
        raise SystemExit(f"missing desktop config: {desktop}")
    patch_desktop(desktop)
    write_cli(cli)
    write_skill(skill)
    # sanity
    text = desktop.read_text(encoding="utf-8")
    assert "custom:orla-ollama" in text
    assert "orla-vl" in text
    assert 'default_profile_id = "custom:orla-ollama"' in text
    print("OK: Orla LLM + orla-vl vision wired")


if __name__ == "__main__":
    main()

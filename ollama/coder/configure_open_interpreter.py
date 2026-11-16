"""Wire Open Interpreter to Coder on Orla (local Ollama). No create/Wan MCP."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

CODER_PROFILE = (
    '{ baseURL = "http://127.0.0.1:11436/v1", codexProfileId = "ollama-coder", '
    'id = "custom:coder-orla", isBuiltin = false, modelId = "coder:latest", '
    'name = "Coder", provider = "local", providerId = "builtin:local", '
    'useResponsesApi = false, wireApi = "chat" }'
)

PROVIDER_BLOCK = """
[model_providers.ollama-coder]
base_url = "http://127.0.0.1:11436/v1"
name = "Ollama (Coder / Orla toolcall proxy)"
requires_openai_auth = false
wire_api = "chat"
"""

CLI_CONFIG = """# Open Interpreter — Coder on Orla (Ren'Py install). No Wan/Forge.
# Hit the toolcall proxy (:11436), not raw Ollama (:11434).
# Start: powershell -File D:\\studio-agent\\ollama\\coder\\start_toolcall_proxy.ps1

model_provider = "ollama-coder"
model = "coder:latest"

[model_providers.ollama-coder]
base_url = "http://127.0.0.1:11436/v1"
name = "Ollama (Coder / Orla toolcall proxy)"
requires_openai_auth = false
wire_api = "chat"
"""


def patch_desktop(cfg_path: Path, *, make_default: bool) -> None:
    bak = cfg_path.with_suffix(cfg_path.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(cfg_path, bak)
    print("backup", bak)
    text = cfg_path.read_text(encoding="utf-8")

    # Drop retired Orla story-editor profile from default if present
    if make_default:
        text = re.sub(
            r'default_profile_id\s*=\s*"custom:orla-ollama"',
            'default_profile_id = "custom:nari-comfybox"',
            text,
        )

    if "custom:coder-orla" not in text:
        if "profiles = [" not in text:
            raise SystemExit("Could not find profiles = [ in desktop config")
        text = text.replace("profiles = [", "profiles = [" + CODER_PROFILE + ", ", 1)
        print("inserted Coder profile")
    else:
        # Keep endpoint on toolcall proxy
        text = re.sub(
            r'(id = "custom:coder-orla"[^\}]*baseURL = ")[^"]+(")',
            r"\g<1>http://127.0.0.1:11436/v1\2",
            text,
        )
        # profiles are single-line objects; patch baseURL near coder-orla
        text = re.sub(
            r'(baseURL = ")http://127\.0\.0\.1:11434/v1(",[^\n]*id = "custom:coder-orla")',
            r"\g<1>http://127.0.0.1:11436/v1\2",
            text,
        )
        text = re.sub(
            r'(id = "custom:coder-orla"[^\n]*?baseURL = ")http://127\.0\.0\.1:11434/v1(")',
            r"\g<1>http://127.0.0.1:11436/v1\2",
            text,
        )
        # Single-line profile: baseURL before id
        text = text.replace(
            'baseURL = "http://127.0.0.1:11434/v1", codexProfileId = "ollama-coder"',
            'baseURL = "http://127.0.0.1:11436/v1", codexProfileId = "ollama-coder"',
        )
        print("Coder profile already present (proxy URL enforced)")

    if "[model_providers.ollama-coder]" not in text:
        if "[mcp_servers.onedesk-mcp]" in text:
            text = text.replace(
                "[mcp_servers.onedesk-mcp]",
                PROVIDER_BLOCK + "\n[mcp_servers.onedesk-mcp]",
            )
        else:
            text += "\n" + PROVIDER_BLOCK
        print("added ollama-coder provider")
    else:
        text = re.sub(
            r'(\[model_providers\.ollama-coder\]\s*\nbase_url\s*=\s*")[^"]+(")',
            r"\g<1>http://127.0.0.1:11436/v1\2",
            text,
        )

    cfg_path.write_text(text, encoding="utf-8")
    print("wrote", cfg_path)


def write_cli(cli_path: Path) -> None:
    cli_path.parent.mkdir(parents=True, exist_ok=True)
    if cli_path.exists():
        bak = cli_path.with_suffix(cli_path.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(cli_path, bak)
    cli_path.write_text(CLI_CONFIG, encoding="utf-8")
    print("wrote CLI coder config", cli_path)
    print("Note: desktop default stays Nari; switch profile to Coder for install work.")


def write_skill(skill_path: Path) -> None:
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).with_name("open_interpreter_SKILL.md")
    skill_path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print("wrote", skill_path)


def write_review_skill(skills_root: Path) -> None:
    dest = skills_root / "code-review-static" / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).parent / "skill-code-review" / "SKILL.md"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print("wrote", dest)


def retire_orla_skill(skills_root: Path) -> None:
    dest = skills_root / "orla-ollama" / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = Path(__file__).resolve().parents[1] / "orla" / "open_interpreter_SKILL.md"
    if src.exists():
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print("retired skill", dest)



def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--default",
        action="store_true",
        help="Do NOT use — Nari should stay desktop default. Flag ignored except scrubbing old orla default.",
    )
    args = ap.parse_args()

    desktop = Path.home() / "AppData/Roaming/Interpreter/codex-home/config.toml"
    if not desktop.exists():
        raise SystemExit(f"missing {desktop}")
    patch_desktop(desktop, make_default=True)
    # Keep a separate CLI snippet for coder sessions
    write_cli(Path.home() / ".openinterpreter/config.coder.toml")
    write_skill(
        Path.home()
        / "AppData/Roaming/Interpreter/codex-home/skills/coder-orla/SKILL.md"
    )
    skills_root = Path.home() / "AppData/Roaming/Interpreter/codex-home/skills"
    write_review_skill(skills_root)
    retire_orla_skill(skills_root)
    print("OK: Coder profile + autonomy skills installed. Use OI profile Coder for review/coding.")


if __name__ == "__main__":
    main()

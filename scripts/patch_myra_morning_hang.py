#!/usr/bin/env python3
"""Fail-fast TTS/brain when ComfyBox sleeps; install morning edge restart cron."""
from __future__ import annotations

import subprocess
from pathlib import Path

HOME = Path.home()
EDGE = HOME / "studio-edge"


def patch_tts() -> None:
    p = EDGE / "studio_edge" / "tts.py"
    t = p.read_text(encoding="utf-8")
    if "Fail fast when ComfyBox is asleep" in t:
        print("tts.py already patched")
        return
    old = (
        "        try:\n"
        "            r = requests.post(\n"
        '                f"{self.narrate_url}/v1/tts",\n'
    )
    if old not in t:
        raise SystemExit("tts.py: post anchor not found")
    new = (
        "        try:\n"
        "            # Fail fast when ComfyBox is asleep/unreachable (common overnight).\n"
        "            if not self.narrate_is_up():\n"
        '                log.warning("Narrate TTS down — skipping Kokoro (voice=%s)", use_voice)\n'
        "                return False\n"
        "            read_s = (\n"
        "                min(self.narrate_timeout_s, 45.0)\n"
        "                if len(text) < 500\n"
        "                else self.narrate_timeout_s\n"
        "            )\n"
        "            r = requests.post(\n"
        '                f"{self.narrate_url}/v1/tts",\n'
    )
    t = t.replace(old, new, 1)
    old_to = (
        "                # Short replies shouldn't wait the full book timeout.\n"
        "                timeout=min(self.narrate_timeout_s, 45.0) if len(text) < 500 else self.narrate_timeout_s,\n"
    )
    new_to = (
        "                # (connect, read) — do not burn 45s waiting for a dead host.\n"
        "                timeout=(2.0, read_s),\n"
    )
    if old_to not in t:
        raise SystemExit("tts.py: timeout anchor not found")
    p.write_text(t.replace(old_to, new_to, 1), encoding="utf-8")
    print("tts.py patched")


def patch_brain() -> None:
    p = EDGE / "studio_edge" / "brain.py"
    t = p.read_text(encoding="utf-8")
    if "Studio brain unreachable at" in t:
        print("brain.py already patched")
        return
    old = (
        "        del force_tool  # Windows MCP owns tool selection\n"
        "        messages = self._messages(user_text)\n"
        "        try:\n"
    )
    if old not in t:
        raise SystemExit("brain.py: ask anchor not found")
    new = (
        "        del force_tool  # Windows MCP owns tool selection\n"
        "        if not self.is_up():\n"
        '            log.error("Studio brain unreachable at %s", self.base_url)\n'
        '            return "I couldn\'t reach Nari on the 8600G. Is Ollama running there?"\n'
        "        messages = self._messages(user_text)\n"
        "        try:\n"
    )
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("brain.py patched")


def install_morning_cron() -> None:
    scripts = EDGE / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    sh = scripts / "morning_edge_restart.sh"
    sh.write_text(
        "#!/usr/bin/env bash\n"
        "# Clear overnight ALSA/USB stale state + dead backend sessions.\n"
        "set -eu\n"
        "exec bash /home/james/studio-edge/restart_edge.sh "
        ">>/tmp/myra-morning-restart.log 2>&1\n",
        encoding="utf-8",
    )
    sh.chmod(0o755)
    proc = subprocess.run(
        ["crontab", "-l"],
        text=True,
        capture_output=True,
    )
    existing = proc.stdout if proc.returncode == 0 else ""
    lines = [ln for ln in existing.splitlines() if "morning_edge_restart" not in ln]
    lines.append(f"15 6 * * * {sh}")
    proc2 = subprocess.run(
        ["crontab", "-"],
        input="\n".join(lines) + "\n",
        text=True,
        capture_output=True,
    )
    if proc2.returncode != 0:
        raise SystemExit(f"crontab install failed: {proc2.stderr}")
    print("cron installed:")
    print(subprocess.check_output(["crontab", "-l"], text=True))


def main() -> int:
    patch_tts()
    patch_brain()
    install_morning_cron()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

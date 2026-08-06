from pathlib import Path

p = Path.home() / "studio-edge" / "config.yaml"
text = p.read_text(encoding="utf-8")
if "studio-recordings" in text:
    print("config already has recording")
else:
    needle = "  notes:\n    enabled: true\n"
    insert = (
        "  notes:\n"
        "    enabled: true\n"
        "  recording:\n"
        "    enabled: true\n"
        "    local_dir: ~/studio-recordings\n"
        '    sync_dir: ""\n'
        "    max_utterance_s: 60\n"
        "    silence_timeout_s: 2.0\n"
        "    post_announce_s: 0.45\n"
    )
    if needle in text:
        p.write_text(text.replace(needle, insert, 1), encoding="utf-8")
        print("config patched")
    else:
        print("WARN notes block missing")

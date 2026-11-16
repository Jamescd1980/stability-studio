#!/usr/bin/env python3
"""Tiny Open Interpreter CLI for Nari — Recycle Bin only, no hard delete.

Usage:
  py -3 D:\\studio-agent\\ollama\\nari\\oi_do.py comfy-queue
  py -3 D:\\studio-agent\\ollama\\nari\\oi_do.py recycle <path>
  py -3 D:\\studio-agent\\ollama\\nari\\oi_do.py docs
  py -3 D:\\studio-agent\\ollama\\nari\\oi_do.py read <doc-id-or-path>
  py -3 D:\\studio-agent\\ollama\\nari\\oi_do.py search <query>
  py -3 D:\\studio-agent\\ollama\\nari\\oi_do.py who <character>
  py -3 D:\\studio-agent\\ollama\\nari\\oi_do.py whoami
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

COMFY = "http://192.168.50.57:8188"
NARI_OLLAMA = "http://192.168.50.57:11434"
MCP_ROOT = Path(r"D:\studio-agent\onedesk-mcp")


def _mcp_path() -> None:
    if str(MCP_ROOT) not in sys.path:
        sys.path.insert(0, str(MCP_ROOT))


def comfy_queue() -> int:
    try:
        with urllib.request.urlopen(f"{COMFY}/queue", timeout=8) as resp:
            queue = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    running = queue.get("queue_running") or []
    pending = queue.get("queue_pending") or []
    print(
        json.dumps(
            {
                "ok": True,
                "queue_running": len(running) if isinstance(running, list) else "?",
                "queue_pending": len(pending) if isinstance(pending, list) else "?",
                "busy": bool(running) or bool(pending),
            },
            indent=2,
        )
    )
    return 0


def recycle(path: str) -> int:
    scripts = Path(r"D:\studio-agent\onedesk-mcp\scripts\general")
    sys.path.insert(0, str(scripts))
    from recycle_path import recycle as _recycle  # type: ignore

    p = Path(path)
    allowed = [
        Path(r"D:\ComfyBox Images and Videos"),
        Path.home() / "Desktop" / "New Images",
    ]
    try:
        resolved = p.resolve()
    except OSError as exc:
        print(f"REFUSED: {exc}")
        return 2
    if not any(
        str(resolved).lower().startswith(str(root.resolve()).lower())
        for root in allowed
        if root.exists()
    ):
        print(f"REFUSED: {resolved} outside delivery / New Images sandbox")
        return 2
    if not resolved.exists():
        print(f"MISSING: {resolved}")
        return 1
    if _recycle(resolved):
        print(f"RECYCLED: {resolved}")
        return 0
    print(f"FAIL: {resolved}")
    return 1


def docs() -> int:
    _mcp_path()
    from studio.doc_reader import list_studio_docs

    print(json.dumps(list_studio_docs(), indent=2, ensure_ascii=False))
    return 0


def read_doc(target: str) -> int:
    _mcp_path()
    from studio.doc_reader import read_studio_doc

    print(
        json.dumps(
            read_studio_doc(doc=target, path=target),
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def search_docs(query: str) -> int:
    _mcp_path()
    from studio.doc_reader import search_studio_docs

    print(json.dumps(search_studio_docs(query), indent=2, ensure_ascii=False))
    return 0


def who(character: str) -> int:
    _mcp_path()
    import yaml
    from studio.character_loras import lookup_character_identity

    catalog = yaml.safe_load(
        (MCP_ROOT / "catalog.yaml").read_text(encoding="utf-8")
    )
    print(
        json.dumps(
            lookup_character_identity(catalog, character),
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def whoami() -> int:
    print("Nari — ComfyBox create brain (Ollama nari @ 192.168.50.57:11434). Orla=polish. Myra=Pi.")
    print(f"Ollama tags: {NARI_OLLAMA}/api/tags")
    print("Docs: oi_do.py docs | read <id> | search <q> | who eris")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help", "help"}:
        print(__doc__.strip())
        return 0
    cmd = argv[1].strip().lower()
    if cmd in {"delete", "rm", "remove", "rmdir", "del", "unlink"}:
        print("REFUSED: Nari cannot hard-delete. Use recycle <path> (Recycle Bin).")
        return 2
    if cmd in {"comfy-queue", "queue", "jobs", "status"}:
        return comfy_queue()
    if cmd in {"recycle", "trash", "bin"}:
        if len(argv) < 3:
            print("usage: oi_do.py recycle <path>")
            return 2
        return recycle(argv[2])
    if cmd in {"docs", "list-docs", "list_docs"}:
        return docs()
    if cmd in {"read", "doc", "cat"}:
        if len(argv) < 3:
            print("usage: oi_do.py read <doc-id-or-path>")
            return 2
        return read_doc(argv[2])
    if cmd in {"search", "grep"}:
        if len(argv) < 3:
            print("usage: oi_do.py search <query>")
            return 2
        return search_docs(" ".join(argv[2:]))
    if cmd in {"who", "identity", "character"}:
        if len(argv) < 3:
            print("usage: oi_do.py who <character>")
            return 2
        return who(" ".join(argv[2:]))
    if cmd in {"whoami", "id"}:
        return whoami()
    print(f"unknown command: {cmd}")
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

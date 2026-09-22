"""Phonetic chapter rewrite for Kokoro readback — DeskHost-owned prep."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


def rewrite_chapter_phonetic(
    cfg: dict[str, Any],
    *,
    text: str = "",
    chapter: int | None = None,
    stem: str = "",
    also_speak: bool = False,
) -> dict[str, Any]:
    """Delegate to DeskHost tools sidecar (Windows :11436) for rewrite + optional Kokoro."""
    orla = cfg.get("orla") or {}
    tools = str(
        orla.get("tools_url")
        or (cfg.get("integrations") or {}).get("orla_tools_url")
        or "http://127.0.0.1:11436"
    ).rstrip("/")
    body = {
        "action": "phonetic_rewrite",
        "text": text,
        "chapter": chapter,
        "stem": stem or (f"chapter_{chapter:02d}" if chapter else "chapter"),
        "also_speak": bool(also_speak),
    }
    if not (text or "").strip():
        return {"ok": False, "error": "text is required"}
    req = urlrequest.Request(
        f"{tools}/action",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=float(orla.get("phonetic_timeout_s") or 180)) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urlerror.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc), "tools_url": tools}
    if not isinstance(data, dict):
        return {"ok": False, "error": "bad response from DeskHost tools"}
    data.setdefault("owner", "orla")
    data.setdefault("doc", "AUDIO-KOKORO.md")
    return data


def slug_stem(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_") or "chapter"

"""Leashed web fetch for CreateBrain — docs / model cards only."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests

# Host allowlist — expand carefully
ALLOWED_HOST_SUFFIXES = (
    "civitai.com",
    "huggingface.co",
    "github.com",
    "githubusercontent.com",
    "gitlab.com",
    "readthedocs.io",
    "readthedocs.org",
    "pytorch.org",
    "comfy.org",
    "stability.ai",
    "docs.google.com",
    "wikipedia.org",
    "fandom.com",
)


def _host_allowed(host: str) -> bool:
    h = (host or "").lower().removeprefix("www.")
    return any(h == s or h.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES)


def _html_to_text(html: str) -> str:
    # Lightweight strip without requiring bs4
    html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p>", "\n\n", html)
    html = re.sub(r"(?is)</(div|h[1-6]|li|tr)>", "\n", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def fetch_web_documentation(url: str, *, max_chars: int = 20000) -> dict[str, Any]:
    """Fetch a URL and return cleaned text (allowlisted hosts only)."""
    raw = (url or "").strip()
    if not raw.startswith(("http://", "https://")):
        return {"ok": False, "error": "url must start with http:// or https://"}
    parsed = urlparse(raw)
    if not _host_allowed(parsed.hostname or ""):
        return {
            "ok": False,
            "error": f"host not allowlisted: {parsed.hostname}",
            "allowed_suffixes": list(ALLOWED_HOST_SUFFIXES),
        }
    try:
        r = requests.get(
            raw,
            timeout=25,
            headers={"User-Agent": "StabilityStudioMCP/CreateBrainDocFetch"},
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc), "url": raw}
    ctype = (r.headers.get("content-type") or "").lower()
    body = r.text
    if "html" in ctype or body.lstrip().startswith("<"):
        text = _html_to_text(body)
    else:
        text = body
    truncated = False
    limit = max(2000, min(int(max_chars or 20000), 80000))
    if len(text) > limit:
        text = text[:limit] + "\n\n…[truncated]…"
        truncated = True
    return {
        "ok": True,
        "url": raw,
        "host": parsed.hostname,
        "chars": len(text),
        "truncated": truncated,
        "content": text,
        "note": "For LoRA installs use download_* MCP tools after you approve the file — scrape ≠ install.",
    }

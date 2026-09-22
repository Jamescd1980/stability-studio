"""Allowlisted .md / .txt reader for CreateBrain and other studio agents.

Roots are sandboxed — no arbitrary filesystem reads.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Short ids → paths (relative to a root key or absolute under an allowlisted root).
DOC_INDEX: dict[str, dict[str, str]] = {
    "lessons-wan-i2v": {
        "title": "Wan 2.2 I2V keepers (MoE, LoRA bundles, Saloon)",
        "path": "stability-studio-mcp/LESSONS-WAN-I2V.md",
        "root": "studio_agent",
    },
    "lessons-nsfw-stills": {
        "title": "NSFW stills / gold finish / waijfu notes",
        "path": "LESSONS-NSFW-STILLS.md",
        "root": "studio_agent",
    },
    "lessons-generation-host-cuda": {
        "title": "GenerationHost CUDA / labor split",
        "path": "LESSONS-COMFYBOX-CUDA.md",
        "root": "studio_agent",
    },
    "lessons-set-fill": {
        "title": "Set fill / mesh / locked plates",
        "path": "LESSONS-SET-FILL.md",
        "root": "studio_agent",
    },
    "lessons-blender": {
        "title": "Blender MCP lessons",
        "path": "LESSONS-BLENDER-MCP.md",
        "root": "studio_agent",
    },
    "lighting-agents": {
        "title": "Lighting / waijfu house bake notes",
        "path": "docs/LIGHTING-AGENTS.md",
        "root": "studio_agent",
    },
    "nari-doc-index": {
        "title": "CreateBrain document index (start here)",
        "path": "ollama/nari/NARI-DOC-INDEX.md",
        "root": "studio_agent",
    },
    "ollama-tools": {
        "title": "Why MCP not Ollama plugins",
        "path": "ollama/nari/OLLAMA-TOOLS.md",
        "root": "studio_agent",
    },
    "nari-skill": {
        "title": "CreateBrain Open Interpreter skill",
        "path": "ollama/nari/open_interpreter_SKILL.md",
        "root": "studio_agent",
    },
    "agents": {
        "title": "Studio AGENTS.md",
        "path": "AGENTS.md",
        "root": "studio_agent",
    },
    "hardware": {
        "title": "Hardware / CreateBrain / Eric / DeskHost map",
        "path": "HARDWARE.md",
        "root": "studio_agent",
    },
    "das-booty-beats": {
        "title": "Das Booty scene beats (TheaterJobs)",
        "path": "Das Booty Beat - Image list.txt",
        "root": "theaterjobs",
    },
    "myra-lessons": {
        "title": "EdgeVoice / studio-edge lessons",
        "path": "handoff/studio_edge/LESSONS-LEARNED.md",
        "root": "studio_agent",
    },
    "path-bible": {
        "title": "CreateBrain/Coder path bible + naming",
        "path": "ollama/coder/PATHS.md",
        "root": "studio_agent",
    },
    "handoff": {
        "title": "TheaterJobs CreateBrain→Coder handoff",
        "path": "staging/handoff.md",
        "root": "theaterjobs",
    },
    "plan-orla-coder": {
        "title": "DeskHost-PC + coder implementation plan",
        "path": "ollama/PLAN-ORLA-CODER.md",
        "root": "studio_agent",
    },
}

ROOTS: dict[str, Path] = {
    "studio_agent": Path(r"D:\studio-agent"),
    "theaterjobs": Path(r"D:\Bad boy\TheaterJobs"),
    "mcp": Path(r"D:\studio-agent\stability-studio-mcp"),
    "cursor_rules": Path(r"D:\studio-agent") / ".cursor" / "rules",
}

ALLOWED_SUFFIXES = {".md", ".txt", ".markdown", ".csv"}


def _roots() -> dict[str, Path]:
    """Resolve roots that exist; skip missing drives quietly."""
    out: dict[str, Path] = {}
    for key, path in ROOTS.items():
        try:
            if path.exists():
                out[key] = path.resolve()
        except OSError:
            continue
    return out


def resolve_safe_path(path_or_id: str) -> tuple[Path | None, str | None]:
    """Return (path, error). Accepts DOC_INDEX id or path under an allowlisted root."""
    raw = (path_or_id or "").strip().strip('"').strip("'")
    if not raw:
        return None, "empty path"
    key = raw.lower().replace("\\", "/").removesuffix(".md").removesuffix(".txt")
    # id lookup
    if raw.lower() in DOC_INDEX or key in DOC_INDEX:
        meta = DOC_INDEX.get(raw.lower()) or DOC_INDEX[key]
        roots = _roots()
        root = roots.get(meta["root"])
        if not root:
            return None, f"root '{meta['root']}' not available on this machine"
        path = (root / meta["path"]).resolve()
        return _validate(path, roots)

    candidate = Path(raw)
    if not candidate.is_absolute():
        # try under studio_agent then mcp
        for root_key in ("studio_agent", "mcp", "theaterjobs"):
            root = _roots().get(root_key)
            if not root:
                continue
            trial = (root / raw).resolve()
            ok, err = _validate(trial, _roots())
            if ok:
                return ok, None
            # keep last err
            last_err = err
        return None, last_err if "last_err" in dir() else "path not under allowlisted roots"

    return _validate(candidate.resolve(), _roots())


def _validate(path: Path, roots: dict[str, Path]) -> tuple[Path | None, str | None]:
    try:
        resolved = path.resolve()
    except OSError as exc:
        return None, str(exc)
    if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
        return None, f"refused: only {sorted(ALLOWED_SUFFIXES)} allowed (got {resolved.suffix})"
    for root in roots.values():
        try:
            resolved.relative_to(root)
            return resolved, None
        except ValueError:
            continue
    return None, f"refused: {resolved} outside allowlisted roots"


def list_studio_docs() -> dict[str, Any]:
    roots = _roots()
    docs = []
    for doc_id, meta in sorted(DOC_INDEX.items()):
        root = roots.get(meta["root"])
        path = (root / meta["path"]) if root else None
        exists = bool(path and path.is_file())
        docs.append(
            {
                "id": doc_id,
                "title": meta["title"],
                "path": str(path) if path else meta["path"],
                "exists": exists,
                "bytes": path.stat().st_size if exists else 0,
            }
        )
    return {
        "ok": True,
        "docs": docs,
        "roots": {k: str(v) for k, v in roots.items()},
        "usage": (
            "read_studio_doc(doc='lessons-wan-i2v') or read_studio_doc(path='LESSONS-NSFW-STILLS.md'). "
            "Also accepts TheaterJobs storyboard .txt under allowlisted roots."
        ),
    }


def read_studio_doc(
    *,
    doc: str = "",
    path: str = "",
    max_chars: int = 24000,
    start_line: int = 1,
    max_lines: int = 0,
    query: str = "",
    context_lines: int = 8,
) -> dict[str, Any]:
    target = (doc or path or "").strip()
    resolved, err = resolve_safe_path(target)
    if err or resolved is None:
        return {
            "ok": False,
            "error": err or "not found",
            "hint": "Call list_studio_docs() for ids, or pass a path under <STUDIO_ROOT> / TheaterJobs.",
        }
    if not resolved.is_file():
        return {"ok": False, "error": f"missing file: {resolved}"}

    text = resolved.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    q = (query or "").strip().lower()

    # Keyword mode: return matching windows instead of the whole file
    if q:
        ctx = max(2, min(int(context_lines or 8), 40))
        chunks: list[str] = []
        hit_lines: list[int] = []
        for i, ln in enumerate(lines):
            if q in ln.lower():
                hit_lines.append(i + 1)
                a = max(0, i - ctx)
                b = min(len(lines), i + ctx + 1)
                window = "\n".join(lines[a:b])
                chunks.append(f"--- lines {a+1}-{b} ---\n{window}")
                if len(chunks) >= 12:
                    break
        if not chunks:
            return {
                "ok": True,
                "path": str(resolved),
                "query": query,
                "hits": 0,
                "content": f"No lines matched {query!r}.",
            }
        content = "\n\n".join(chunks)
        truncated = False
        limit = max(2000, min(int(max_chars or 24000), 100_000))
        if len(content) > limit:
            content = content[:limit] + "\n\n…[truncated]…"
            truncated = True
        return {
            "ok": True,
            "path": str(resolved),
            "doc_id": doc or None,
            "query": query,
            "hits": len(hit_lines),
            "hit_lines": hit_lines[:40],
            "chars": len(content),
            "truncated": truncated,
            "content": content,
        }

    start = max(1, int(start_line or 1))
    if max_lines and max_lines > 0:
        chunk_lines = lines[start - 1 : start - 1 + max_lines]
    else:
        chunk_lines = lines[start - 1 :]
    chunk = "\n".join(chunk_lines)
    truncated = False
    limit = max(2000, min(int(max_chars or 24000), 100_000))
    if len(chunk) > limit:
        chunk = chunk[:limit] + "\n\n…[truncated]…"
        truncated = True

    headings = [
        ln.strip()
        for ln in lines[:400]
        if ln.startswith("#") or re.match(r"^=+$", ln.strip())
    ][:40]

    return {
        "ok": True,
        "path": str(resolved),
        "doc_id": doc or None,
        "start_line": start,
        "line_count": len(lines),
        "chars": len(chunk),
        "truncated": truncated,
        "headings_preview": headings,
        "content": chunk,
    }


def append_lesson(doc: str, bullet: str, *, heading: str = "") -> dict[str, Any]:
    """Append one factual bullet to an allowlisted lessons .md file."""
    allowed = {
        "lessons-wan-i2v",
        "lessons-nsfw-stills",
        "lessons-generation-host-cuda",
        "lessons-set-fill",
        "lessons-blender",
        "myra-lessons",
        "lighting-agents",
    }
    key = (doc or "").strip().lower()
    if key not in allowed:
        return {
            "ok": False,
            "error": f"append not allowed for {doc!r}",
            "allowed": sorted(allowed),
        }
    text = (bullet or "").strip()
    if not text:
        return {"ok": False, "error": "empty bullet"}
    # One short bullet — reject dumps
    if len(text) > 600 or text.count("\n") > 4:
        return {
            "ok": False,
            "error": "bullet too long — one factual lesson only (≤600 chars, ≤4 lines)",
        }
    if not text.startswith("-"):
        text = f"- {text}"
    resolved, err = resolve_safe_path(key)
    if err or resolved is None:
        return {"ok": False, "error": err or "missing"}
    from datetime import date

    stamp = date.today().isoformat()
    block = ""
    if heading.strip():
        block += f"\n### {heading.strip()}\n"
    block += f"\n{text}  \n<!-- appended {stamp} via append_lesson -->\n"
    with resolved.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return {
        "ok": True,
        "path": str(resolved),
        "doc": key,
        "appended": text,
        "date": stamp,
    }


def search_studio_docs(query: str, max_hits: int = 20) -> dict[str, Any]:
    q = (query or "").strip().lower()
    if len(q) < 2:
        return {"ok": False, "error": "query too short"}
    hits: list[dict[str, Any]] = []
    for row in list_studio_docs()["docs"]:
        if not row.get("exists"):
            continue
        path = Path(row["path"])
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if q in line.lower():
                hits.append(
                    {
                        "id": row["id"],
                        "path": row["path"],
                        "line": i,
                        "text": line.strip()[:240],
                    }
                )
                if len(hits) >= max_hits:
                    return {"ok": True, "query": query, "hits": hits}
    return {"ok": True, "query": query, "hits": hits}

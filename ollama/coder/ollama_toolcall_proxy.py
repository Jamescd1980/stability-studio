#!/usr/bin/env python3
"""Coder tool-call fixup proxy for Orla.

qwen2.5-coder via Ollama often returns tool invocations as JSON *text in
content* instead of OpenAI `message.tool_calls`. Open Interpreter / Codex only
executes real tool_calls — so Coder looks like it "can't code."

OI / clients hit :11436; real Ollama stays on :11434.
"""
from __future__ import annotations

import json
import re
import uuid
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

UPSTREAM = "http://127.0.0.1:11434"
LISTEN = ("127.0.0.1", 11436)

_JSON_OBJ = re.compile(r"\{[\s\S]*\}")
_TOOL_XML = re.compile(
    r"<tool_call>\s*([\s\S]*?)\s*</tool_call>", re.IGNORECASE
)
_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _try_parse_obj(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_OBJ.search(text)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _extract_tool_blob(content: str) -> dict[str, Any] | None:
    if not content or not isinstance(content, str):
        return None
    raw = content.strip()
    for m in _TOOL_XML.finditer(raw):
        obj = _try_parse_obj(m.group(1))
        if obj and ("name" in obj or "function" in obj):
            return obj
    for m in _FENCE.finditer(raw):
        obj = _try_parse_obj(m.group(1))
        if obj and ("name" in obj or "function" in obj):
            return obj
    obj = _try_parse_obj(raw)
    if obj and ("name" in obj or "function" in obj):
        return obj
    # Loose: first {"name": ...} in the string
    idx = raw.find('{"name"')
    if idx < 0:
        idx = raw.find("{\n  \"name\"")
    if idx >= 0:
        obj = _try_parse_obj(raw[idx:])
        if obj and ("name" in obj or "function" in obj):
            return obj
    return None


def _normalize_call(
    blob: dict[str, Any], available: set[str]
) -> tuple[str, str] | None:
    """Return (tool_name, arguments_json_string)."""
    name = blob.get("name")
    args = blob.get("arguments", blob.get("parameters", {}))
    if isinstance(blob.get("function"), dict):
        name = blob["function"].get("name") or name
        args = blob["function"].get("arguments", args)

    if not name or not isinstance(name, str):
        return None

    # Classic Open Interpreter "execute" → Codex shell when present
    if name == "execute" and "shell" in available:
        lang = ""
        code = ""
        if isinstance(args, dict):
            lang = str(args.get("language") or "")
            code = str(args.get("code") or "")
        if code:
            if lang.lower() in ("powershell", "pwsh", "shell", "bash", "cmd", ""):
                if lang.lower() in ("powershell", "pwsh"):
                    cmd = ["powershell.exe", "-Command", code]
                elif lang.lower() == "cmd":
                    cmd = ["cmd.exe", "/c", code]
                else:
                    cmd = ["powershell.exe", "-Command", code]
                name = "shell"
                args = {"command": cmd}
            else:
                # python / other — keep as shell invoking interpreter when possible
                name = "shell"
                args = {
                    "command": [
                        "powershell.exe",
                        "-Command",
                        code if lang.lower() != "python" else f"python -c {json.dumps(code)}",
                    ]
                }

    if available and name not in available and "shell" in available:
        # Unknown name but looks like a command payload → shell
        if isinstance(args, dict) and (
            "command" in args or "cmd" in args or "code" in args
        ):
            if "command" not in args and "code" in args:
                args = {
                    "command": [
                        "powershell.exe",
                        "-Command",
                        str(args.get("code")),
                    ]
                }
            name = "shell"

    if isinstance(args, str):
        args_s = args
    else:
        args_s = json.dumps(args if args is not None else {})
    return name, args_s


def _available_tools(req: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    tools = req.get("tools") or []
    if not isinstance(tools, list):
        return out
    for t in tools:
        if not isinstance(t, dict):
            continue
        if t.get("type") == "function" and isinstance(t.get("function"), dict):
            n = t["function"].get("name")
            if isinstance(n, str):
                out.add(n)
        n2 = t.get("name")
        if isinstance(n2, str):
            out.add(n2)
    return out


def _rewrite_message(msg: dict[str, Any], available: set[str]) -> bool:
    """Mutate message in place. True if rewritten."""
    if not isinstance(msg, dict):
        return False
    existing = msg.get("tool_calls")
    if isinstance(existing, list) and existing:
        return False
    blob = _extract_tool_blob(str(msg.get("content") or ""))
    if not blob:
        return False
    norm = _normalize_call(blob, available)
    if not norm:
        return False
    name, args_s = norm
    msg["content"] = None
    msg["tool_calls"] = [
        {
            "id": f"call_{uuid.uuid4().hex[:24]}",
            "type": "function",
            "function": {"name": name, "arguments": args_s},
        }
    ]
    return True


def _rewrite_completion(data: dict[str, Any], available: set[str]) -> dict[str, Any]:
    choices = data.get("choices")
    if not isinstance(choices, list):
        return data
    for ch in choices:
        if not isinstance(ch, dict):
            continue
        msg = ch.get("message")
        if _rewrite_message(msg if isinstance(msg, dict) else {}, available):
            ch["finish_reason"] = "tool_calls"
            # Some clients look at message without finish_reason
    return data


def _as_sse(data: dict[str, Any]) -> bytes:
    """Minimal chat.completion.chunk stream carrying tool_calls."""
    cid = data.get("id") or f"chatcmpl-{uuid.uuid4().hex[:12]}"
    model = data.get("model") or "coder:latest"
    msg = {}
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        msg = {"role": "assistant", "content": data}
    role_chunk = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": data.get("created") or 0,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    delta: dict[str, Any] = {}
    if msg.get("tool_calls"):
        # Stream tool_calls in one chunk (index required)
        tcs = []
        for i, tc in enumerate(msg["tool_calls"]):
            tcs.append(
                {
                    "index": i,
                    "id": tc.get("id"),
                    "type": "function",
                    "function": tc.get("function") or {},
                }
            )
        delta["tool_calls"] = tcs
    elif msg.get("content"):
        delta["content"] = msg["content"]
    tool_chunk = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": data.get("created") or 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": "tool_calls" if msg.get("tool_calls") else "stop",
            }
        ],
    }
    parts = [
        f"data: {json.dumps(role_chunk, ensure_ascii=False)}\n\n",
        f"data: {json.dumps(tool_chunk, ensure_ascii=False)}\n\n",
        "data: [DONE]\n\n",
    ]
    return "".join(parts).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        line = fmt % args
        if any(x in line.lower() for x in ("error", "11436", "tool")):
            super().log_message(fmt, *args)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        path = self.path.split("?", 1)[0]
        want_stream = False
        available: set[str] = set()
        req_obj: dict[str, Any] | None = None

        if body and path in ("/v1/chat/completions", "/chat/completions"):
            try:
                req_obj = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                req_obj = None
            if isinstance(req_obj, dict):
                available = _available_tools(req_obj)
                want_stream = bool(req_obj.get("stream"))
                # Force buffered upstream so we can rewrite tool JSON → tool_calls
                if req_obj.get("tools") or want_stream:
                    req_obj = dict(req_obj)
                    req_obj["stream"] = False
                    body = json.dumps(req_obj).encode("utf-8")

        url = UPSTREAM + self.path
        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding")
        }
        if body:
            headers["Content-Length"] = str(len(body))
        req = urllib.request.Request(
            url, data=body or None, headers=headers, method=self.command
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                out = resp.read()
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if (
                    req_obj is not None
                    and path in ("/v1/chat/completions", "/chat/completions")
                    and "json" in ctype
                ):
                    try:
                        data = json.loads(out.decode("utf-8"))
                        if isinstance(data, dict):
                            data = _rewrite_completion(data, available)
                            if want_stream:
                                out = _as_sse(data)
                                ctype = "text/event-stream; charset=utf-8"
                            else:
                                out = json.dumps(data, ensure_ascii=False).encode(
                                    "utf-8"
                                )
                                ctype = "application/json"
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass

                self.send_response(resp.status)
                skip = {
                    "transfer-encoding",
                    "connection",
                    "content-length",
                    "content-type",
                }
                for k, v in resp.headers.items():
                    if k.lower() in skip:
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Type", ctype or "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(out)
        except urllib.error.HTTPError as e:
            out = e.read()
            self.send_response(e.code)
            self.send_header(
                "Content-Type", e.headers.get("Content-Type", "application/json")
            )
            self.send_header("Content-Length", str(len(out)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(out)
        except Exception as e:  # noqa: BLE001
            out = json.dumps({"error": str(e)}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

    def do_GET(self) -> None:  # noqa: N802
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._proxy()


def main() -> None:
    server = ThreadingHTTPServer(LISTEN, Handler)
    print(
        f"coder toolcall proxy on {LISTEN[0]}:{LISTEN[1]} -> {UPSTREAM}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()

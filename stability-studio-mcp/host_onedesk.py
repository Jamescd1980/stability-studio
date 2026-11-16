#!/usr/bin/env python3
"""One Desk MCP host — second process over local HTTP JSON.

Desk talks to this host; tool code stays in this folder (not inside OneDesk.exe).

  python host_onedesk.py --port 7872
  OneDeskMcp.exe --port 7872
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ONEDESK_MCP_SHIP", "1")

from onedesk_ship import ROOM_TOOLS, identity_payload, write_identity  # noqa: E402

_MOD: Any = None
_LOAD_ERROR: str | None = None
_LOAD_LOCK = threading.RLock()
_GPU_LOCK = threading.Lock()
_GPU_TOOLS = frozenset(
    {
        "generate_image",
        "edit_image",
        "generate_image_i2i",
        "generate_image_guided",
        "refine_face_forge",
        "refine_image_forge",
        "refine_region_forge",
        "generate_video",
        "switch_stills_backend",
    }
)


def _load_server() -> dict[str, Any]:
    global _MOD, _LOAD_ERROR
    with _LOAD_LOCK:
        if _MOD is not None:
            return {"ok": True, "path": str(ROOT), "tool_count": _tool_count()}
        try:
            import importlib.util

            server_py = ROOT / "server.py"
            if not server_py.is_file():
                _LOAD_ERROR = f"server.py missing under {ROOT}"
                return {"ok": False, "error": _LOAD_ERROR}
            # Ensure identity exists for ship_mode_enabled()
            write_identity(ROOT)
            os.environ["ONEDESK_MCP_SHIP"] = "1"
            spec = importlib.util.spec_from_file_location("one_desk_mcp_server_host", server_py)
            if spec is None or spec.loader is None:
                _LOAD_ERROR = "Could not load server.py"
                return {"ok": False, "error": _LOAD_ERROR}
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _MOD = mod
            _LOAD_ERROR = None
            return {"ok": True, "path": str(ROOT), "tool_count": _tool_count()}
        except Exception as exc:  # noqa: BLE001
            _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
            _MOD = None
            return {"ok": False, "error": _LOAD_ERROR, "trace": traceback.format_exc()}


def _tool_count() -> int:
    mcp = getattr(_MOD, "mcp", None) if _MOD is not None else None
    tools = getattr(getattr(mcp, "_tool_manager", None), "_tools", None)
    return len(tools) if isinstance(tools, dict) else 0


def _resolve_fn(name: str) -> Callable[..., Any] | None:
    if _MOD is None:
        return None
    fn = getattr(_MOD, name, None)
    if fn is None:
        return None
    if hasattr(fn, "fn"):
        return fn.fn
    if hasattr(fn, "__wrapped__"):
        return fn.__wrapped__  # type: ignore[return-value]
    return fn


def _invoke(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    if name not in ROOM_TOOLS:
        return {"ok": False, "error": f"Tool not in One Desk ship set: {name}"}
    loaded = _load_server()
    if not loaded.get("ok"):
        return loaded
    fn = _resolve_fn(name)
    if fn is None:
        return {"ok": False, "error": f"Tool missing in server: {name}"}
    args = dict(arguments or {})
    try:
        result = fn(**args)
        if not isinstance(result, (str, dict, list)):
            result = str(result)
        return {"ok": True, "name": name, "result": result}
    except TypeError as exc:
        return {"ok": False, "error": f"Bad arguments for {name}: {exc}", "arguments": args}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "name": name}


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if name in _GPU_TOOLS:
        with _GPU_LOCK:
            return _invoke(name, arguments)
    return _invoke(name, arguments)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        sys.stderr.write("[onedesk-mcp-host] " + (fmt % args) + "\n")

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in {"/health", "/"}:
            self._send(200, {"ok": True, "service": "onedesk-mcp-host"})
            return
        if path == "/identity":
            self._send(200, {"ok": True, **identity_payload()})
            return
        if path == "/status":
            st = _load_server()
            self._send(
                200,
                {
                    **st,
                    "identity": identity_payload(),
                    "error": _LOAD_ERROR,
                },
            )
            return
        self._send(404, {"ok": False, "error": f"Unknown path {path}"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        body = self._read_json()
        if path == "/call":
            name = str(body.get("name") or "").strip()
            args = body.get("arguments")
            if not isinstance(args, dict):
                args = body.get("args") if isinstance(body.get("args"), dict) else {}
            if not name:
                self._send(400, {"ok": False, "error": "name required"})
                return
            self._send(200, call_tool(name, args))
            return
        if path == "/reload":
            global _MOD, _LOAD_ERROR
            with _LOAD_LOCK:
                _MOD = None
                _LOAD_ERROR = None
                sys.modules.pop("one_desk_mcp_server_host", None)
            self._send(200, _load_server())
            return
        self._send(404, {"ok": False, "error": f"Unknown path {path}"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One Desk MCP HTTP host")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7872)
    parser.add_argument("--preload", action="store_true", help="Load server.py before accept")
    args = parser.parse_args(argv)

    write_identity(ROOT)
    os.environ["ONEDESK_MCP_SHIP"] = "1"

    if args.preload:
        print(json.dumps(_load_server()), flush=True)

    httpd = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(
        f"[onedesk-mcp-host] listening on http://{args.host}:{args.port}  root={ROOT}",
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

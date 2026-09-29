#!/usr/bin/env python3
"""Tiny reverse proxy: inject think=false / reasoning_effort=none for Qwen3.

OI and other OpenAI-compat clients hit :11435; real Ollama stays on :11434.
Eric is patched separately to send think:false on /api/generate.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "http://127.0.0.1:11434"
LISTEN = ("127.0.0.1", 11435)
INJECT_PATHS = {
    "/v1/chat/completions",
    "/api/chat",
    "/api/generate",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # quieter
        if "error" in (fmt % args).lower():
            super().log_message(fmt, *args)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        path = self.path.split("?", 1)[0]

        if body and path in INJECT_PATHS:
            try:
                data = json.loads(body.decode("utf-8"))
                if isinstance(data, dict):
                    data["think"] = False
                    data["reasoning_effort"] = "none"
                    opts = data.get("options")
                    if isinstance(opts, dict):
                        opts.pop("think", None)
                    body = json.dumps(data).encode("utf-8")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        url = UPSTREAM + self.path
        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding")
        }
        if body:
            headers["Content-Length"] = str(len(body))
        req = urllib.request.Request(url, data=body or None, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                out = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() in ("transfer-encoding", "connection", "content-length"):
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(out)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(out)
        except urllib.error.HTTPError as e:
            out = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
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
    # Bind all interfaces so Windows OI can reach ComfyBox:11435
    server = ThreadingHTTPServer(("0.0.0.0", LISTEN[1]), Handler)
    print(f"ollama nothink proxy on 0.0.0.0:{LISTEN[1]} -> {UPSTREAM}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

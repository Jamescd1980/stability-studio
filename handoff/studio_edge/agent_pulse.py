"""Pulse Myra / Nari / Orla status to ComfyBox status server for the ultrawide widget."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any
from urllib.request import Request, urlopen

log = logging.getLogger("studio_edge.agent_pulse")

_lock = threading.Lock()
_state: dict[str, Any] = {
    "myra": {"status": "listening", "detail": "Wake word", "ok": True},
}
_stop = threading.Event()
_thread: threading.Thread | None = None
_status_url = "http://192.168.50.57:7870"


def configure(cfg: dict | None = None) -> None:
    global _status_url
    d = (cfg or {}).get("display") or {}
    raw = str(d.get("status_url") or "http://192.168.50.57:7870/status")
    _status_url = raw.split("/status")[0].rstrip("/") or "http://192.168.50.57:7870"


def set_status(
    agent_id: str,
    status: str,
    *,
    detail: str = "",
    ok: bool = True,
    name: str | None = None,
    role: str | None = None,
) -> None:
    """Update local state; POST in a daemon thread so the voice loop never blocks."""
    aid = (agent_id or "").strip().lower()
    if not aid:
        return
    with _lock:
        cur = dict(_state.get(aid) or {})
        cur.update(
            {
                "status": status.strip().lower().replace(" ", "_"),
                "detail": detail or "",
                "ok": ok,
            }
        )
        if name:
            cur["name"] = name
        if role:
            cur["role"] = role
        _state[aid] = cur
    threading.Thread(
        target=_post_one, args=(aid,), name=f"pulse-{aid}", daemon=True
    ).start()


def _post_one(aid: str) -> None:
    with _lock:
        payload = dict(_state.get(aid) or {})
    if not payload:
        return
    body = {
        "id": aid,
        "status": payload.get("status", "ready"),
        "detail": payload.get("detail", ""),
        "ok": bool(payload.get("ok", True)),
    }
    if payload.get("name"):
        body["name"] = payload["name"]
    if payload.get("role"):
        body["role"] = payload["role"]
    # Defaults for known agents
    if aid == "myra":
        body.setdefault("name", "Myra")
        body.setdefault("role", "Gofor · Pi")
    elif aid == "nari":
        body.setdefault("name", "Nari")
        body.setdefault("role", "Create · ComfyBox")
    elif aid == "orla":
        body.setdefault("name", "Orla")
        body.setdefault("role", "Polish · Windows")
    try:
        data = json_dumps(body)
        req = Request(
            f"{_status_url}/agent",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=1.5) as r:
            r.read()
    except Exception as exc:  # noqa: BLE001
        log.debug("agent pulse failed: %s", exc)


def json_dumps(obj: dict) -> bytes:
    import json

    return json.dumps(obj).encode("utf-8")


def _loop() -> None:
    while not _stop.is_set():
        with _lock:
            ids = list(_state.keys())
        for aid in ids:
            _post_one(aid)
        _stop.wait(4.0)


def start(cfg: dict | None = None) -> None:
    global _thread
    configure(cfg)
    set_status("myra", "listening", detail="Wake word", ok=True)
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="agent-pulse", daemon=True)
    _thread.start()
    log.info("Agent pulse → %s/agent", _status_url)


def stop() -> None:
    _stop.set()

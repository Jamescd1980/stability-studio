#!/usr/bin/env python3
"""ComfyBox status API for Myra's ultrawide widget.

GET  /status  -> GPU + agent roster JSON
POST /agent   -> {id, status, detail?, ok?}  (Myra heartbeats / work pulses)
GET  /health  -> ok

Run on comfybox:
  python3 status_server.py --port 7870 --listen 0.0.0.0
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

CACHE_TTL = 1.0
_cache: dict = {"t": 0.0, "data": {}}
_agent_lock = threading.Lock()
# id -> {name, role, status, detail, ok, updated}
_agents: dict[str, dict] = {}

DEFAULT_AGENTS = (
    {
        "id": "myra",
        "name": "Myra",
        "role": "Gofor · Pi",
        "status": "unknown",
        "detail": "Waiting for heartbeat",
        "ok": True,
    },
    {
        "id": "nari",
        "name": "Nari",
        "role": "Create · ComfyBox",
        "status": "unknown",
        "detail": "",
        "ok": True,
    },
    {
        "id": "orla",
        "name": "Orla",
        "role": "Polish · Windows",
        "status": "unknown",
        "detail": "",
        "ok": True,
    },
)

# Seconds without Myra heartbeat → hung
MYRA_STALE_S = float(os.environ.get("MYRA_STALE_S", "18"))
NARI_URL = os.environ.get("NARI_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
ORLA_TOOLS_URL = os.environ.get(
    "ORLA_TOOLS_URL", "http://192.168.50.42:11436"
).rstrip("/")
ORLA_OLLAMA_URL = os.environ.get(
    "ORLA_OLLAMA_URL", "http://192.168.50.42:11434"
).rstrip("/")


def _run(cmd: list[str], timeout: float = 2.5) -> str:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (r.stdout or "") + (r.stderr or "")
    except Exception:
        return ""


def _pgrep(pattern: str) -> list[str]:
    out = _run(["pgrep", "-af", pattern])
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return [ln for ln in lines if "pgrep" not in ln]


def _systemctl_active(unit: str) -> bool:
    out = _run(["systemctl", "is-active", unit], timeout=2.0).strip().splitlines()
    return bool(out and out[0].strip() == "active")


def _http_json(url: str, timeout: float = 1.2) -> dict | list | None:
    try:
        req = Request(url, headers={"User-Agent": "comfybox-status/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _http_ok(url: str, timeout: float = 1.2) -> bool:
    try:
        req = Request(url, headers={"User-Agent": "comfybox-status/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 500
    except Exception:
        return False


def _ensure_defaults() -> None:
    with _agent_lock:
        for row in DEFAULT_AGENTS:
            if row["id"] not in _agents:
                _agents[row["id"]] = {**row, "updated": 0.0}


def upsert_agent(body: dict) -> dict:
    _ensure_defaults()
    aid = str(body.get("id") or "").strip().lower()
    if not aid:
        return {"ok": False, "error": "id required"}
    with _agent_lock:
        cur = dict(_agents.get(aid) or {"id": aid, "name": aid.title(), "role": ""})
        if body.get("name"):
            cur["name"] = str(body["name"])
        if body.get("role"):
            cur["role"] = str(body["role"])
        if body.get("status"):
            cur["status"] = str(body["status"]).strip().lower().replace(" ", "_")
        if "detail" in body:
            cur["detail"] = str(body.get("detail") or "")
        if "ok" in body:
            cur["ok"] = bool(body["ok"])
        cur["updated"] = time.time()
        cur["id"] = aid
        _agents[aid] = cur
        return {"ok": True, "agent": cur}


def _probe_nari() -> dict:
    tags = _http_json(f"{NARI_URL}/api/tags", timeout=1.0)
    if tags is None:
        return {
            "status": "error",
            "detail": "Ollama unreachable",
            "ok": False,
        }
    ps = _http_json(f"{NARI_URL}/api/ps", timeout=1.0) or {}
    models = ps.get("models") or []
    busy = any(
        "nari" in str(m.get("name") or m.get("model") or "").lower()
        for m in models
        if isinstance(m, dict)
    )
    if busy:
        return {"status": "thinking", "detail": "Model loaded", "ok": True}
    return {"status": "ready", "detail": "Ollama up", "ok": True}


def _probe_orla() -> dict:
    tools = _http_json(f"{ORLA_TOOLS_URL}/status", timeout=1.2)
    ollama_up = _http_ok(f"{ORLA_OLLAMA_URL}/api/tags", timeout=1.0)
    if tools and tools.get("ok"):
        return {
            "status": "ready",
            "detail": "Tools online",
            "ok": True,
        }
    if ollama_up:
        return {
            "status": "ready",
            "detail": "Ollama up, tools offline",
            "ok": True,
        }
    return {
        "status": "error",
        "detail": "Windows Orla unreachable",
        "ok": False,
    }


def _roster(gpu_job: str, gpu_detail: str | None) -> list[dict]:
    """Merge heartbeats + probes. Myra stale → hung."""
    _ensure_defaults()
    now = time.time()
    with _agent_lock:
        snap = {k: dict(v) for k, v in _agents.items()}

    # Probes fill gaps when no recent pulse (except Myra — heartbeat only)
    nari = snap.get("nari") or {}
    if now - float(nari.get("updated") or 0) > 8:
        probed = _probe_nari()
        # If GPU is generating and Nari not recently pulsed as working, show working
        if gpu_job in {"generating", "queued", "training"} and probed.get("ok"):
            probed = {
                "status": "working",
                "detail": gpu_detail or gpu_job,
                "ok": True,
            }
        nari = {
            **DEFAULT_AGENTS[1],
            **nari,
            **probed,
            "updated": nari.get("updated") or 0,
        }
        snap["nari"] = nari

    orla = snap.get("orla") or {}
    if now - float(orla.get("updated") or 0) > 8:
        probed = _probe_orla()
        orla = {**DEFAULT_AGENTS[2], **orla, **probed, "updated": orla.get("updated") or 0}
        snap["orla"] = orla

    myra = snap.get("myra") or dict(DEFAULT_AGENTS[0])
    age = now - float(myra.get("updated") or 0)
    if myra.get("updated") and age > MYRA_STALE_S:
        myra = {
            **myra,
            "status": "hung",
            "detail": f"No heartbeat {int(age)}s",
            "ok": False,
        }
    elif not myra.get("updated"):
        myra = {
            **DEFAULT_AGENTS[0],
            "status": "error",
            "detail": "No heartbeat yet",
            "ok": False,
        }
    snap["myra"] = myra

    order = ["myra", "nari", "orla"]
    out = []
    for aid in order:
        row = snap.get(aid) or next(a for a in DEFAULT_AGENTS if a["id"] == aid)
        out.append(
            {
                "id": row.get("id", aid),
                "name": row.get("name", aid.title()),
                "role": row.get("role", ""),
                "status": row.get("status", "unknown"),
                "detail": row.get("detail", ""),
                "ok": bool(row.get("ok", True)),
                "updated": int(row.get("updated") or 0),
                "age_s": int(max(0, now - float(row.get("updated") or 0)))
                if row.get("updated")
                else None,
            }
        )
    # Any extras
    for aid, row in snap.items():
        if aid in order:
            continue
        out.append(
            {
                "id": aid,
                "name": row.get("name", aid),
                "role": row.get("role", ""),
                "status": row.get("status", "unknown"),
                "detail": row.get("detail", ""),
                "ok": bool(row.get("ok", True)),
                "updated": int(row.get("updated") or 0),
                "age_s": None,
            }
        )
    return out


def _rocm_gpu() -> dict:
    info = {
        "gpu_name": "Radeon RX 7900 XT",
        "gpu_temp_c": None,
        "gpu_power_w": None,
        "gpu_vram_pct": None,
        "gpu_util_pct": None,
        "gpu_sclk_mhz": None,
        "gpu_mclk_mhz": None,
    }
    raw = _run(
        [
            "rocm-smi",
            "--showtemp",
            "--showuse",
            "--showmeminfo",
            "vram",
            "--showproductname",
            "--json",
        ],
        timeout=3.0,
    )
    if raw.strip().startswith("{"):
        try:
            data = json.loads(raw)
            card = None
            for k, v in data.items():
                if isinstance(v, dict) and (
                    "Temperature" in str(v) or "GPU use" in str(v) or "VRAM" in str(v)
                ):
                    card = v
                    break
            if not card and data:
                card = next(iter(data.values()))
            if isinstance(card, dict):
                for key, val in card.items():
                    kl = key.lower()
                    if "temperature" in kl and "edge" in kl:
                        try:
                            info["gpu_temp_c"] = float(str(val).replace("C", "").strip())
                        except ValueError:
                            pass
                    elif kl == "gpu use (%)" or "gpu use" in kl:
                        try:
                            info["gpu_util_pct"] = float(str(val).replace("%", "").strip())
                        except ValueError:
                            pass
        except json.JSONDecodeError:
            pass

    concise = _run(["rocm-smi"], timeout=3.0)
    for line in concise.splitlines():
        if re.match(r"^\s*0\s+", line) or (line.strip().startswith("0") and "0x744c" in line):
            temps = re.findall(r"(\d+(?:\.\d+)?)°C", line)
            if temps:
                try:
                    info["gpu_temp_c"] = float(temps[0])
                except ValueError:
                    pass
            pcts = re.findall(r"(\d+)%", line)
            if len(pcts) >= 2:
                try:
                    info["gpu_vram_pct"] = float(pcts[-2])
                    info["gpu_util_pct"] = float(pcts[-1])
                except ValueError:
                    pass
            mhz = re.findall(r"(\d+)Mhz", line, re.I)
            if mhz:
                try:
                    info["gpu_sclk_mhz"] = float(mhz[0])
                    if len(mhz) > 1:
                        info["gpu_mclk_mhz"] = float(mhz[1])
                except ValueError:
                    pass
            powers = re.findall(r"(\d+(?:\.\d+)?)W", line)
            if powers:
                try:
                    info["gpu_power_w"] = float(powers[0])
                except ValueError:
                    pass
            break

    mem = _run(["rocm-smi", "--showmeminfo", "vram"], timeout=2.5)
    total = used = None
    for line in mem.splitlines():
        if "GPU[0]" in line and "Total Memory" in line:
            m = re.search(r":\s*(\d+)", line)
            if m:
                total = int(m.group(1))
        if "GPU[0]" in line and "Total Used Memory" in line:
            m = re.search(r"(:\s*)(\d+)", line)
            if m:
                used = int(m.group(2))
    if total and used is not None and total > 0:
        info["gpu_vram_pct"] = round(100.0 * used / total, 1)
        info["gpu_vram_used_gb"] = round(used / (1024**3), 2)
        info["gpu_vram_total_gb"] = round(total / (1024**3), 2)

    return info


def _cpu_temp_c() -> float | None:
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            name = (h / "name").read_text().strip()
        except Exception:
            continue
        if name != "k10temp":
            continue
        for fname in ("temp1_input", "temp2_input", "temp3_input"):
            p = h / fname
            if not p.exists():
                continue
            try:
                t = int(p.read_text().strip()) / 1000.0
                if 10 <= t <= 110:
                    return t
            except Exception:
                continue
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            name = (h / "name").read_text().strip()
        except Exception:
            continue
        if name in {"amdgpu", "nvme"}:
            continue
        p = h / "temp1_input"
        if not p.exists():
            continue
        try:
            t = int(p.read_text().strip()) / 1000.0
            if 20 <= t <= 110:
                return t
        except Exception:
            continue
    return None


def _training_detail() -> str | None:
    lines = _pgrep("sdxl_train_network|train_network.py|kohya")
    if not lines:
        chains = _pgrep("_train_flamme_ubel_chain|_train_lora_comfybox")
        if chains:
            return "LoRA train chain"
        return None
    blob = " ".join(lines)
    m = re.search(r"--output_name=([^\s]+)", blob)
    if m:
        return f"Training {m.group(1)}"
    for name in ("flamme", "ubel", "fern", "frieren", "makima"):
        if name in blob.lower():
            return f"Training {name.title()}"
    return "Training LoRA"


def _comfy_job(comfy_url: str) -> tuple[str, int, str | None]:
    q = _http_json(f"{comfy_url.rstrip('/')}/queue")
    if q is None:
        return "offline", 0, None
    running = q.get("queue_running") or []
    pending = q.get("queue_pending") or []
    rem = len(running) + len(pending)
    if running:
        return "generating", rem, "ComfyUI generating"
    if pending:
        return "queued", rem, f"ComfyUI queue {rem}"
    return "idle", 0, None


def collect_status(comfy_url: str, forge_url: str) -> dict:
    now = time.time()
    if now - _cache["t"] < CACHE_TTL and _cache["data"]:
        # Refresh agent roster even on cache hit (cheap + heartbeat-sensitive)
        data = dict(_cache["data"])
        data["agents"] = _roster(str(data.get("job") or "idle"), data.get("detail"))
        data["ts"] = int(now)
        return data

    comfy_active = _systemctl_active("comfyui")
    forge_procs = _pgrep("launch.py|webui.sh")
    forge_up = any("launch.py" in p or "webui" in p.lower() for p in forge_procs)

    train = _training_detail()
    gpu = _rocm_gpu()
    cpu_temp = _cpu_temp_c()

    backend = "idle"
    job = "idle"
    detail = None
    queue_remaining = 0

    if train:
        backend = "training"
        job = "training"
        detail = train
    elif forge_up:
        backend = "forge"
        util = gpu.get("gpu_util_pct") or 0
        if util and util > 15:
            job = "generating"
            detail = "Forge busy"
        else:
            job = "idle"
            detail = "Forge ready"
    elif comfy_active:
        backend = "comfy"
        state, queue_remaining, detail = _comfy_job(comfy_url)
        job = state if state != "offline" else "idle"
        if state == "offline":
            detail = "ComfyUI service up, API offline"
        elif state == "idle":
            detail = "ComfyUI ready"
    else:
        backend = "idle"
        job = "idle"
        detail = "GPU idle"

    narrate = bool(_pgrep("narrate-tts|kokoro"))

    data = {
        "ok": True,
        "host": "comfybox",
        "ts": int(now),
        "backend": backend,
        "job": job,
        "detail": detail,
        "queue_remaining": queue_remaining,
        "comfy_active": comfy_active,
        "forge_active": forge_up,
        "training": bool(train),
        "narrate_active": narrate,
        "cpu_temp_c": cpu_temp,
        "agents": _roster(job, detail),
        **gpu,
    }
    _cache["t"] = now
    _cache["data"] = data
    return data


class Handler(BaseHTTPRequestHandler):
    comfy_url = "http://127.0.0.1:8188"
    forge_url = "http://127.0.0.1:7860"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, b"")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/health"):
            self._send(200, b'{"ok":true}')
            return
        if path.startswith("/status"):
            data = collect_status(self.comfy_url, self.forge_url)
            self._send(200, json.dumps(data).encode("utf-8"))
            return
        self._send(404, b'{"error":"not found"}')

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/agent", "/agents"}:
            self._send(404, b'{"error":"not found"}')
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, b'{"ok":false,"error":"invalid json"}')
            return
        if not isinstance(body, dict):
            self._send(400, b'{"ok":false,"error":"object required"}')
            return
        # Allow batch: {"agents":[...]}
        if isinstance(body.get("agents"), list):
            results = [upsert_agent(a) for a in body["agents"] if isinstance(a, dict)]
            self._send(200, json.dumps({"ok": True, "results": results}).encode("utf-8"))
            return
        result = upsert_agent(body)
        self._send(200 if result.get("ok") else 400, json.dumps(result).encode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7870)
    ap.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    ap.add_argument("--forge-url", default="http://127.0.0.1:7860")
    args = ap.parse_args()
    Handler.comfy_url = args.comfy_url
    Handler.forge_url = args.forge_url
    _ensure_defaults()
    httpd = ThreadingHTTPServer((args.listen, args.port), Handler)
    print(
        f"comfybox-status listening on http://{args.listen}:{args.port}/status",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

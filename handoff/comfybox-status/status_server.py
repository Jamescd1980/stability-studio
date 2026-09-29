#!/usr/bin/env python3
"""Generation-host status + heat API for the desktop heat monitor widget.

GET  /status  -> GPU heat + agent roster JSON (includes nari_device)
POST /agent   -> {id, status, detail?, ok?}
GET  /health  -> ok

Typical:
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
)

MYRA_STALE_S = float(os.environ.get("MYRA_STALE_S", "18"))
NARI_URL = os.environ.get("NARI_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
# Optional labels for the discrete NVIDIA card vs APU iGPU
NARI_DGPU_LABEL = os.environ.get("NARI_DGPU_LABEL", "5090")
NARI_IGPU_LABEL = os.environ.get("NARI_IGPU_LABEL", "iGPU")


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
        req = Request(url, headers={"User-Agent": "comfybox-heat-monitor/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


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


def _ollama_on_nvidia() -> bool:
    """True if an ollama runner is using the discrete NVIDIA GPU."""
    raw = _run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_gpu_memory",
            "--format=csv,noheader",
        ],
        timeout=2.5,
    ).lower()
    if not raw.strip() or "failed" in raw:
        return False
    return "ollama" in raw


def _ollama_cuda_env_hint() -> str | None:
    """Read CUDA_VISIBLE_DEVICES from a running ollama serve process, if any."""
    pids = _run(["pgrep", "-f", "ollama serve"]).strip().split()
    for pid in pids:
        if not pid.isdigit():
            continue
        try:
            env = Path(f"/proc/{pid}/environ").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        for part in env.split("\x00"):
            if part.startswith("CUDA_VISIBLE_DEVICES="):
                return part.split("=", 1)[1].strip()
    return None


def _probe_nari_placement() -> dict:
    """Where Nari / nari-prompt is loaded: 5090 (dGPU), iGPU, CPU, or unloaded."""
    tags = _http_json(f"{NARI_URL}/api/tags", timeout=1.0)
    if tags is None:
        return {
            "nari_device": "error",
            "nari_device_label": "?",
            "nari_loaded": False,
            "nari_models": [],
            "status": "error",
            "detail": "Ollama unreachable",
            "ok": False,
        }

    ps = _http_json(f"{NARI_URL}/api/ps", timeout=1.2) or {}
    models = [m for m in (ps.get("models") or []) if isinstance(m, dict)]
    nari_models = [
        str(m.get("name") or m.get("model") or "")
        for m in models
        if "nari" in str(m.get("name") or m.get("model") or "").lower()
    ]
    loaded = bool(nari_models)
    on_nvidia = _ollama_on_nvidia()
    cuda_vis = _ollama_cuda_env_hint()

    if not loaded:
        device = "unloaded"
        label = "â€”"
        # Preference / policy hint from systemd env when idle
        if cuda_vis == "" or cuda_vis == "-1":
            prefer = NARI_IGPU_LABEL
        elif cuda_vis is not None:
            prefer = NARI_DGPU_LABEL
        else:
            prefer = None
        detail = f"Ollama up Â· prefer {prefer}" if prefer else "Ollama up"
        return {
            "nari_device": device,
            "nari_device_label": label,
            "nari_loaded": False,
            "nari_models": [],
            "nari_prefer_label": prefer,
            "status": "ready",
            "detail": detail,
            "ok": True,
        }

    # Loaded: decide where the weights live
    vram_sizes = []
    for m in models:
        name = str(m.get("name") or m.get("model") or "")
        if "nari" not in name.lower():
            continue
        try:
            vram_sizes.append(int(m.get("size_vram") or 0))
        except (TypeError, ValueError):
            vram_sizes.append(0)
    any_vram = any(v > 0 for v in vram_sizes)

    if on_nvidia or (cuda_vis not in {None, "", "-1"} and any_vram):
        device = "dgpu"
        label = NARI_DGPU_LABEL
    elif any_vram:
        # VRAM reported but not on NVIDIA â†’ APU / iGPU carve-out
        device = "igpu"
        label = NARI_IGPU_LABEL
    else:
        device = "cpu"
        label = "CPU"

    return {
        "nari_device": device,
        "nari_device_label": label,
        "nari_loaded": True,
        "nari_models": nari_models,
        "status": "thinking",
        "detail": f"On {label}",
        "ok": True,
    }


def _probe_nari() -> dict:
    return _probe_nari_placement()


def _roster(gpu_job: str, gpu_detail: str | None, nari_place: dict) -> list[dict]:
    _ensure_defaults()
    now = time.time()
    with _agent_lock:
        snap = {k: dict(v) for k, v in _agents.items()}

    nari = snap.get("nari") or {}
    if now - float(nari.get("updated") or 0) > 8:
        probed = dict(nari_place)
        if gpu_job in {"generating", "queued", "training"} and probed.get("ok"):
            probed["status"] = "working"
            if not probed.get("detail"):
                probed["detail"] = gpu_detail or gpu_job
        nari = {
            **DEFAULT_AGENTS[1],
            **nari,
            **probed,
            "updated": nari.get("updated") or 0,
        }
        snap["nari"] = nari
    else:
        # Keep live placement fields even on heartbeat rows
        nari = {
            **nari,
            "nari_device": nari_place.get("nari_device"),
            "nari_device_label": nari_place.get("nari_device_label"),
            "nari_loaded": nari_place.get("nari_loaded"),
        }
        snap["nari"] = nari

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

    order = ["myra", "nari"]
    out = []
    for aid in order:
        row = snap.get(aid) or next(a for a in DEFAULT_AGENTS if a["id"] == aid)
        item = {
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
        if aid == "myra":
            role = str(item.get("role") or "")
            if "gofor" in role.lower() or not role.strip():
                item["role"] = "Gofor · Pi"
        if aid == "nari":
            item["role"] = "Create · ComfyBox"
            item["device"] = row.get("nari_device_label") or nari_place.get(
                "nari_device_label"
            )
            item["device_id"] = row.get("nari_device") or nari_place.get("nari_device")
            item["loaded"] = bool(
                row.get("nari_loaded")
                if "nari_loaded" in row
                else nari_place.get("nari_loaded")
            )
        out.append(item)
    for aid, row in snap.items():
        if aid in order:
            continue
        role = str(row.get("role", "") or "")
        if str(aid).lower() == "orla" or "polish" in role.lower():
            if str(aid).lower() == "orla" or "orla" in str(row.get("name") or "").lower():
                role = "Coder · Windows"
        out.append(
            {
                "id": aid,
                "name": row.get("name", aid),
                "role": role,
                "status": row.get("status", "unknown"),
                "detail": row.get("detail", ""),
                "ok": bool(row.get("ok", True)),
                "updated": int(row.get("updated") or 0),
                "age_s": None,
            }
        )
    return out


def _empty_gpu(name: str = "GPU") -> dict:
    return {
        "gpu_name": name,
        "gpu_temp_c": None,
        "gpu_power_w": None,
        "gpu_vram_pct": None,
        "gpu_vram_used_gb": None,
        "gpu_vram_total_gb": None,
        "gpu_util_pct": None,
        "gpu_sclk_mhz": None,
        "gpu_mclk_mhz": None,
        "gpu_fan_rpm": None,
    }


def _nvidia_gpu() -> dict | None:
    raw = _run(
        [
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,clocks.gr,clocks.mem",
            "--format=csv,noheader,nounits",
        ],
        timeout=3.0,
    ).strip()
    if not raw or "NVIDIA-SMI has failed" in raw or "failed" in raw.lower():
        return None
    line = raw.splitlines()[0].strip()
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 8:
        return None
    info = _empty_gpu(parts[0] or "NVIDIA GPU")

    def _f(i: int) -> float | None:
        try:
            v = parts[i]
            if v in {"", "[N/A]", "N/A"}:
                return None
            return float(v)
        except (IndexError, ValueError):
            return None

    info["gpu_temp_c"] = _f(1)
    info["gpu_util_pct"] = _f(2)
    used_mib = _f(3)
    total_mib = _f(4)
    info["gpu_power_w"] = _f(5)
    info["gpu_sclk_mhz"] = _f(6)
    info["gpu_mclk_mhz"] = _f(7)
    if used_mib is not None and total_mib and total_mib > 0:
        info["gpu_vram_used_gb"] = round(used_mib / 1024.0, 2)
        info["gpu_vram_total_gb"] = round(total_mib / 1024.0, 2)
        info["gpu_vram_pct"] = round(100.0 * used_mib / total_mib, 1)
    return info


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def _amdgpu_sysfs_gpu() -> dict | None:
    best: dict | None = None
    best_vram = -1
    for card in Path("/sys/class/drm").glob("card*"):
        if "-" in card.name:
            continue
        dev = card / "device"
        try:
            vendor = (dev / "vendor").read_text().strip()
        except Exception:
            continue
        if vendor != "0x1002":
            continue
        vram_total = _read_int(dev / "mem_info_vram_total") or 0
        if vram_total <= best_vram:
            continue
        try:
            device_id = (dev / "device").read_text().strip()
        except Exception:
            device_id = ""
        name = "AMD Radeon" if device_id else "AMD GPU"
        info = _empty_gpu(name)
        used = _read_int(dev / "mem_info_vram_used")
        info["gpu_util_pct"] = _read_int(dev / "gpu_busy_percent")
        if used is not None and vram_total > 0:
            info["gpu_vram_used_gb"] = round(used / (1024**3), 2)
            info["gpu_vram_total_gb"] = round(vram_total / (1024**3), 2)
            info["gpu_vram_pct"] = round(100.0 * used / vram_total, 1)
        hwmon_root = dev / "hwmon"
        if hwmon_root.is_dir():
            for h in hwmon_root.glob("hwmon*"):
                temp = _read_int(h / "temp1_input")
                if temp is not None:
                    info["gpu_temp_c"] = round(temp / 1000.0, 1)
                power = _read_int(h / "power1_average")
                if power is not None:
                    info["gpu_power_w"] = round(power / 1_000_000.0, 1)
                break
        best = info
        best_vram = vram_total
    return best


def _gpu() -> dict:
    nv = _nvidia_gpu()
    if nv is not None:
        return nv
    sysfs = _amdgpu_sysfs_gpu()
    if sysfs is not None:
        return sysfs
    return _empty_gpu("GPU")


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
    return None


def _training_detail() -> str | None:
    lines = _pgrep("sdxl_train_network|train_network.py|kohya")
    if not lines:
        return None
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
    nari_place = _probe_nari_placement()
    if now - _cache["t"] < CACHE_TTL and _cache["data"]:
        data = dict(_cache["data"])
        data["agents"] = _roster(str(data.get("job") or "idle"), data.get("detail"), nari_place)
        data["ts"] = int(now)
        data.update(
            {
                "nari_device": nari_place.get("nari_device"),
                "nari_device_label": nari_place.get("nari_device_label"),
                "nari_loaded": nari_place.get("nari_loaded"),
                "nari_models": nari_place.get("nari_models") or [],
            }
        )
        return data

    comfy_active = _systemctl_active("comfyui")
    forge_procs = _pgrep("launch.py|webui.sh")
    forge_up = any("launch.py" in p or "webui" in p.lower() for p in forge_procs)

    train = _training_detail()
    gpu = _gpu()
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

    data = {
        "ok": True,
        "host": os.environ.get("STATUS_HOST_NAME", "comfybox"),
        "ts": int(now),
        "backend": backend,
        "job": job,
        "detail": detail,
        "queue_remaining": queue_remaining,
        "comfy_active": comfy_active,
        "forge_active": forge_up,
        "training": bool(train),
        "cpu_temp_c": cpu_temp,
        "nari_device": nari_place.get("nari_device"),
        "nari_device_label": nari_place.get("nari_device_label"),
        "nari_loaded": nari_place.get("nari_loaded"),
        "nari_models": nari_place.get("nari_models") or [],
        "agents": _roster(job, detail, nari_place),
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
        if isinstance(body.get("agents"), list):
            results = [upsert_agent(a) for a in body["agents"] if isinstance(a, dict)]
            self._send(200, json.dumps({"ok": True, "results": results}).encode("utf-8"))
            return
        result = upsert_agent(body)
        self._send(200 if result.get("ok") else 400, json.dumps(result).encode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
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
        f"heat-monitor status listening on http://{args.listen}:{args.port}/status",
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

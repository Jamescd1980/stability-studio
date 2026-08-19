"""Fetch ComfyUI outputs from the remote host when /view 404s.

Comfybox writes videos under <MODELS_MOUNT>/... (Game NTFS). That is not the same disk as
Windows <DELIVERY> (StudioWork). The /view API only serves
--output-directory (<MODELS_MOUNT>/comfyui-output); VHS often lands elsewhere (e.g. Video/).
"""

from __future__ import annotations

import base64
import shlex
import subprocess
from pathlib import Path
from typing import Any


_DEFAULT_REMOTE_DIRS = (
    "<MODELS_MOUNT>/comfyui-output",
    "<MODELS_MOUNT>/ComfyBox Images and Videos/Video",
    "<MODELS_MOUNT>/ComfyBox Images and Videos/Images",
    "<MODELS_MOUNT>/comfyui-temp",
)

_DEFAULT_SEARCH_ROOTS = (
    "<MODELS_MOUNT>/comfyui-output",
    "<MODELS_MOUNT>/ComfyBox Images and Videos",
)


def ssh_host(cfg: dict[str, Any]) -> str:
    comfy = cfg.get("comfyui") or {}
    if comfy.get("ssh_host"):
        return str(comfy["ssh_host"])
    forge = cfg.get("forge") or {}
    return str(forge.get("ssh_host") or "comfybox")


def remote_output_dirs(cfg: dict[str, Any]) -> list[str]:
    comfy = cfg.get("comfyui") or {}
    raw = comfy.get("remote_output_dirs")
    if isinstance(raw, list) and raw:
        return [str(x) for x in raw]
    return list(_DEFAULT_REMOTE_DIRS)


def remote_search_roots(cfg: dict[str, Any]) -> list[str]:
    comfy = cfg.get("comfyui") or {}
    raw = comfy.get("remote_search_roots")
    if isinstance(raw, list) and raw:
        return [str(x) for x in raw]
    return list(_DEFAULT_SEARCH_ROOTS)


def _ssh_run(host: str, remote_cmd: str, *, timeout: int = 180) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, remote_cmd],
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def locate_remote_file(
    cfg: dict[str, Any],
    *,
    filename: str,
    subfolder: str = "",
) -> str | None:
    """Return absolute path on the SSH host, or None if not found."""
    if not filename:
        return None
    host = ssh_host(cfg)
    dirs = remote_output_dirs(cfg)
    roots = remote_search_roots(cfg)
    # One remote Python call — avoids quoting hell with spaces in paths.
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        f"name = {filename!r}\n"
        f"sub = {subfolder or ''!r}\n"
        f"dirs = {dirs!r}\n"
        f"roots = {roots!r}\n"
        "cands = []\n"
        "for d in dirs:\n"
        "    base = Path(d)\n"
        "    if sub:\n"
        "        cands.append(base / sub / name)\n"
        "    cands.append(base / name)\n"
        "for p in cands:\n"
        "    if p.is_file() and p.stat().st_size > 0:\n"
        "        print(p)\n"
        "        sys.exit(0)\n"
        "hits = []\n"
        "for root in roots:\n"
        "    r = Path(root)\n"
        "    if not r.is_dir():\n"
        "        continue\n"
        "    try:\n"
        "        hits.extend([p for p in r.rglob(name) if p.is_file() and p.stat().st_size > 0])\n"
        "    except OSError:\n"
        "        pass\n"
        "if hits:\n"
        "    hits.sort(key=lambda p: p.stat().st_mtime, reverse=True)\n"
        "    print(hits[0])\n"
        "    sys.exit(0)\n"
        "sys.exit(1)\n"
    )
    proc = _ssh_run(host, f"python3 -c {shlex.quote(script)}", timeout=60)
    if proc.returncode != 0:
        return None
    path = proc.stdout.decode("utf-8", errors="replace").strip().splitlines()
    return path[0].strip() if path else None


def fetch_remote_file(
    cfg: dict[str, Any],
    remote_path: str,
    dest: Path,
    *,
    timeout: int = 300,
) -> Path:
    """Copy remote_path from SSH host to dest via base64 (handles spaces in paths)."""
    host = ssh_host(cfg)
    dest.parent.mkdir(parents=True, exist_ok=True)
    quoted = shlex.quote(remote_path)
    proc = _ssh_run(host, f"base64 -w0 {quoted}", timeout=timeout)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")[-500:]
        raise RuntimeError(f"SSH fetch failed for {remote_path} via {host}: {err}")
    raw = base64.b64decode(proc.stdout)
    if not raw:
        raise RuntimeError(f"SSH fetch returned empty file: {remote_path}")
    dest.write_bytes(raw)
    return dest


def fetch_comfy_output_via_ssh(
    cfg: dict[str, Any],
    file_info: dict[str, Any],
    dest_dir: Path,
) -> Path:
    """Locate filename on comfybox and copy into dest_dir."""
    filename = str(file_info.get("filename") or "")
    subfolder = str(file_info.get("subfolder") or "")
    remote = locate_remote_file(cfg, filename=filename, subfolder=subfolder)
    if not remote:
        raise FileNotFoundError(
            f"Remote file not found on {ssh_host(cfg)} for {filename!r} "
            f"(searched output dirs + ComfyBox Video/Images). "
            "ComfyUI /view 404 usually means the file is on the Game drive, not Windows D:."
        )
    dest = dest_dir / Path(filename).name
    return fetch_remote_file(cfg, remote, dest)

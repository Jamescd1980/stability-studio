"""Myra display control — blank/wake, idle clock face, ComfyBox kiosk."""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

log = logging.getLogger("studio_edge.display")

PID_KIOSK = Path("/tmp/myra-display-kiosk.pid")
PID_IDLE = Path("/tmp/myra-swayidle.pid")
# Legacy pid from earlier ComfyBox-only kiosk
PID_STATUS_LEGACY = Path("/tmp/myra-comfybox-status.pid")

ASSETS = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_STATUS_HTML = ASSETS / "comfybox_status.html"
DEFAULT_IDLE_HTML = ASSETS / "myra_idle.html"
KIOSK_CLASS = "myra-display-kiosk"
# Separate Chromium profile — required so --kiosk is not swallowed by the
# desktop Chromium single-instance (which left a mid-screen window on the bar).
KIOSK_USER_DATA = Path.home() / "studio-edge" / ".chromium-kiosk"


def _display_cfg(cfg: dict) -> dict:
    d = dict(cfg.get("display") or {})
    d.setdefault("enabled", True)
    d.setdefault("wayland_display", "wayland-0")
    d.setdefault("xdg_runtime_dir", f"/run/user/{os.getuid()}")
    d.setdefault("output", "HDMI-A-1")
    # Native IPS 4"×12" strip — preferred EDID mode, not 1080p
    d.setdefault("mode", "1920x515")
    d.setdefault("status_url", "http://192.168.50.57:7870/status")
    d.setdefault("status_html", str(DEFAULT_STATUS_HTML))
    d.setdefault("idle_html", str(DEFAULT_IDLE_HTML))
    d.setdefault("screensaver_idle_s", 300)
    d.setdefault("temp_unit", "F")
    d.setdefault("browser", "chromium")
    d.setdefault("show_idle_on_start", True)
    return d


def _window_size(cfg: dict) -> str:
    mode = str(_display_cfg(cfg).get("mode") or "1920x515")
    return mode.replace("x", ",")


def _env(cfg: dict) -> dict:
    d = _display_cfg(cfg)
    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = str(d["xdg_runtime_dir"])
    env["WAYLAND_DISPLAY"] = str(d["wayland_display"])
    env.setdefault("DISPLAY", ":0")
    return env


def _run(cmd: list[str], cfg: dict, *, timeout: float = 8.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        env=_env(cfg),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid(path: Path) -> int | None:
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    if _pid_alive(pid):
        return pid
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    return None


def _write_pid(path: Path, pid: int) -> None:
    try:
        path.write_text(str(pid), encoding="utf-8")
    except OSError as exc:
        log.warning("Could not write pid %s: %s", path, exc)


def _kill_pidfile(path: Path, *, name: str) -> bool:
    pid = _read_pid(path)
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    deadline = time.time() + 3.0
    while time.time() < deadline and _pid_alive(pid):
        time.sleep(0.1)
    if _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    log.info("Stopped %s (pid %s)", name, pid)
    return True


def _stop_kiosk(cfg: dict) -> None:
    _kill_pidfile(PID_KIOSK, name="display-kiosk")
    _kill_pidfile(PID_STATUS_LEGACY, name="comfybox-status-legacy")
    _run(["pkill", "-f", KIOSK_CLASS], cfg)
    _run(["pkill", "-f", "myra-comfybox-status"], cfg)
    _run(["pkill", "-f", str(KIOSK_USER_DATA)], cfg)


def _start_kiosk(cfg: dict, html: Path, query: str = "") -> bool:
    """Launch Chromium kiosk on the Wayland seat. Returns True on launch."""
    if not html.is_file():
        log.error("Kiosk HTML missing: %s", html)
        return False
    _stop_kiosk(cfg)
    time.sleep(0.2)
    url = html.as_uri()
    if query:
        url = f"{url}?{query.lstrip('?')}"
    browser = str(_display_cfg(cfg).get("browser") or "chromium")
    try:
        KIOSK_USER_DATA.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.warning("Could not create kiosk profile dir: %s", exc)
    win = _window_size(cfg)
    cmd = [
        browser,
        f"--user-data-dir={KIOSK_USER_DATA}",
        "--ozone-platform=wayland",
        f"--app={url}",
        f"--class={KIOSK_CLASS}",
        "--kiosk",
        "--start-fullscreen",
        f"--window-size={win}",
        "--window-position=0,0",
        "--noerrdialogs",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        "--disable-features=TranslateUI",
        "--check-for-update-interval=31536000",
        "--autoplay-policy=no-user-gesture-required",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            env=_env(cfg),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        log.error("Failed to launch kiosk: %s", exc)
        return False
    # Chromium may fork; confirm the pid (or a child with our profile) survives.
    time.sleep(0.8)
    if not _pid_alive(proc.pid):
        # Parent exited after handing off — find the real kiosk process.
        r = _run(["pgrep", "-f", str(KIOSK_USER_DATA)], cfg)
        kids = [int(x) for x in (r.stdout or "").split() if x.isdigit()]
        if not kids:
            log.error("Kiosk exited immediately (no process for %s)", KIOSK_USER_DATA)
            return False
        _write_pid(PID_KIOSK, kids[0])
        log.info("Display kiosk pid=%s (reaped parent) url=%s size=%s", kids[0], url, win)
        return True
    _write_pid(PID_KIOSK, proc.pid)
    log.info("Display kiosk pid=%s url=%s size=%s", proc.pid, url, win)
    return True


def blank_screen(cfg: dict) -> str:
    """Turn the panel off (power save / night mode)."""
    d = _display_cfg(cfg)
    if not d.get("enabled", True):
        return "Display control is turned off in my config."
    out = str(d["output"])
    r = _run(["wlopm", "--off", out], cfg)
    if r.returncode != 0:
        log.warning("wlopm --off failed: %s %s", r.stderr, r.stdout)
        return "I couldn't blank the screen."
    return "Screen blanked. Sleep well."


def wake_screen(cfg: dict) -> str:
    """Turn the panel back on."""
    d = _display_cfg(cfg)
    if not d.get("enabled", True):
        return "Display control is turned off in my config."
    out = str(d["output"])
    r = _run(["wlopm", "--on", out], cfg)
    if r.returncode != 0:
        log.warning("wlopm --on failed: %s %s", r.stderr, r.stdout)
        return "I couldn't wake the screen."
    return "Screen is on."


def enable_screensaver(cfg: dict) -> str:
    """Blank now and arm idle auto-blank (swayidle)."""
    d = _display_cfg(cfg)
    if not d.get("enabled", True):
        return "Display control is turned off in my config."
    idle_s = max(30, int(d.get("screensaver_idle_s", 300)))
    out = str(d["output"])
    _kill_pidfile(PID_IDLE, name="swayidle")
    blank_screen(cfg)
    cmd = [
        "swayidle",
        "-w",
        "timeout",
        str(idle_s),
        f"wlopm --off {out}",
        "resume",
        f"wlopm --on {out}",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            env=_env(cfg),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        log.error("swayidle start failed: %s", exc)
        return "Screen is blanked, but I couldn't arm the auto screensaver."
    _write_pid(PID_IDLE, proc.pid)
    mins = max(1, idle_s // 60)
    return f"Screensaver on. Screen blanked, and it'll blank again after {mins} minutes idle."


def disable_screensaver(cfg: dict) -> str:
    """Wake the panel and stop auto-blank."""
    stopped = _kill_pidfile(PID_IDLE, name="swayidle")
    wake = wake_screen(cfg)
    if stopped:
        return "Screensaver off. " + wake
    return wake


def ensure_display_mode(cfg: dict, mode: str | None = None) -> None:
    """Lock the bar panel to its native mode (default 1920x515 ultrawide).

    This IPS 4\"×12\" strip reports 1920x515 as preferred. Forcing 1080p
    stretches/letterboxes the idle face into a middle band.
    """
    d = _display_cfg(cfg)
    out = str(d.get("output") or "HDMI-A-1")
    mode = str(mode or d.get("mode") or "1920x515")
    r = _run(["wlr-randr", "--output", out, "--mode", mode], cfg)
    if r.returncode != 0:
        log.warning("wlr-randr mode %s failed: %s %s", mode, r.stderr, r.stdout)
    else:
        log.info("Display %s set to %s", out, mode)


def show_idle_face(cfg: dict) -> str:
    """Wake panel and show Myra clock / idle face."""
    d = _display_cfg(cfg)
    if not d.get("enabled", True):
        return "Display control is turned off in my config."
    html = Path(os.path.expanduser(str(d["idle_html"]))).resolve()
    wake_screen(cfg)
    ensure_display_mode(cfg)
    if not _start_kiosk(cfg, html):
        return "I couldn't open my idle display."
    return "Back to my clock face."


def hide_comfybox_status(cfg: dict) -> str:
    """Leave ComfyBox status and return to the idle clock face."""
    return show_idle_face(cfg)


def show_comfybox_status(cfg: dict) -> str:
    """Wake panel and open full-screen ComfyBox status kiosk."""
    d = _display_cfg(cfg)
    if not d.get("enabled", True):
        return "Display control is turned off in my config."

    html = Path(os.path.expanduser(str(d["status_html"]))).resolve()
    if not html.is_file():
        log.error("Status HTML missing: %s", html)
        return "I couldn't find the ComfyBox status page."

    unit = str(d.get("temp_unit", "F")).upper()
    if unit not in {"F", "C"}:
        unit = "F"
    query = (
        "url="
        + quote(str(d["status_url"]), safe="")
        + f"&unit={unit}&poll=1500"
    )
    wake_screen(cfg)
    ensure_display_mode(cfg)
    if not _start_kiosk(cfg, html, query):
        return "I couldn't open the ComfyBox status display."
    return "ComfyBox status is on the screen."


def maybe_show_idle_on_start(cfg: dict) -> None:
    """Best-effort idle face when studio-edge boots."""
    d = _display_cfg(cfg)
    if not d.get("enabled", True) or not d.get("show_idle_on_start", True):
        return
    try:
        show_idle_face(cfg)
    except Exception as exc:  # noqa: BLE001
        log.warning("Idle face on start failed: %s", exc)

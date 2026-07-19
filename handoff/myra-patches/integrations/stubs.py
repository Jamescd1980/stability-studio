"""Spoken stubs for tools that need LAN/cloud services not yet wired."""
from __future__ import annotations


def _off(name: str, how: str) -> str:
    return (
        f"{name} isn't hooked up yet. When you're ready, we'll use {how}. "
        "I can still do timers, notes, weather, and search."
    )


def thermostat_status(cfg: dict) -> str:
    ha = (cfg.get("integrations") or {}).get("home_assistant") or {}
    if ha.get("enabled") and ha.get("base_url") and ha.get("token"):
        return "Thermostat integration is marked enabled, but the live client isn't installed yet."
    return _off("The thermostat", "Home Assistant climate entities")


def thermostat_set(cfg: dict, temperature_f: float | None = None, mode: str = "") -> str:
    del temperature_f, mode
    return thermostat_status(cfg)


def calendar_next(cfg: dict) -> str:
    cal = (cfg.get("integrations") or {}).get("calendar") or {}
    if cal.get("enabled"):
        return "Calendar is marked enabled, but the live client isn't installed yet."
    return _off("Calendar", "a local CalDAV or Google calendar read-only feed")


def lights_control(cfg: dict, action: str = "", room: str = "") -> str:
    del action, room
    ha = (cfg.get("integrations") or {}).get("home_assistant") or {}
    if ha.get("enabled"):
        return "Lights are marked enabled, but the live client isn't installed yet."
    return _off("Lights", "Home Assistant light entities")


def traffic_eta(cfg: dict, destination: str = "") -> str:
    del destination
    tr = (cfg.get("integrations") or {}).get("traffic") or {}
    if tr.get("enabled"):
        return "Traffic is marked enabled, but the live client isn't installed yet."
    return _off("Traffic", "a maps API key or a Home Assistant travel-time sensor")


def package_status(cfg: dict, query: str = "") -> str:
    del query
    pk = (cfg.get("integrations") or {}).get("packages") or {}
    if pk.get("enabled"):
        return "Package tracking is marked enabled, but the live client isn't installed yet."
    return _off("Package tracking", "17track or a carrier API plus a local tracking list")


def studio_mcp_bridge_status(cfg: dict) -> str:
    br = (cfg.get("integrations") or {}).get("studio_mcp_bridge") or {}
    if br.get("enabled"):
        return "Studio MCP bridge is marked enabled, but the proxy isn't running yet."
    return (
        "Nari can't call Windows MCP tools yet. Groundwork is in config under "
        "integrations.studio_mcp_bridge — we'll point it at the Windows stability-studio MCP next."
    )

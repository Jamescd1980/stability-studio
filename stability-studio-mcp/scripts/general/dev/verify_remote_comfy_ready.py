"""Smoke-check catalog + remote ComfyUI readiness for Jan/MCP."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.catalog import StyleCatalog
from studio.comfy_remote_models import clear_comfy_model_cache, remote_model_inventory
from studio.config import catalog_path, load_config


def main() -> int:
    clear_comfy_model_cache()
    cfg = load_config()
    cat = StyleCatalog(catalog_path(cfg), cfg)
    remote = remote_model_inventory(cfg)
    print("comfyui", cfg.get("comfyui", {}).get("url"))
    print("hardware", cfg.get("hardware"))
    print(
        "remote",
        remote.get("reachable"),
        "ckpts",
        len(remote.get("checkpoints") or []),
        "loras",
        len(remote.get("loras") or []),
    )
    ctx = cat.get_generation_context()
    sr = ctx["style_readiness"]["summary"]
    ready = sorted(k for k, v in sr.items() if v.get("ready"))
    not_ready = sorted((k, v.get("missing_count")) for k, v in sr.items() if not v.get("ready"))
    print("checkpoints_installed", len(ctx["checkpoints_installed"]))
    print("ready_styles", ready)
    print("not_ready", not_ready)
    print("jan_quickstart", ctx.get("jan_quickstart"))
    wf = [v["file"] for v in ctx["video_workflow_files"]]
    print("workflow_files_ok", wf)
    for sid in [
        "anime",
        "ilustmix",
        "waijfu",
        "perfection_25d",
        "fantasy_prime",
        "n4mik4",
        "miracle_nsfw",
        "homochi",
        "noobai_vpred",
    ]:
        key = cat._find_style_key(sid)
        st = cat.styles[key]
        print(f"{sid}: {st.get('checkpoint')} ready={sr.get(key, {}).get('ready')}")
    ok = remote.get("reachable") and "ilustmix" in ready and "anime" in ready
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

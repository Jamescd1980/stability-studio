# -*- coding: utf-8 -*-
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

cfg = Path(__file__).resolve().parents[2] / "config.yaml"
text = cfg.read_text(encoding="utf-8")
m = re.search(r'api_key:\s*"([^"]+)"', text) or re.search(r"api_key:\s*'([^']+)'", text)
if not m:
    m = re.search(r"api_key:\s*(\S+)", text)
key = m.group(1).strip().strip('"').strip("'")
H = {"Authorization": f"Bearer {key}", "User-Agent": "onedesk-mcp"}


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode())


def show_model(mid: int) -> None:
    m = get(f"https://civitai.com/api/v1/models/{mid}")
    print("=" * 60)
    print(m.get("id"), m.get("name"))
    desc = re.sub(r"<[^>]+>", " ", m.get("description") or "")
    desc = re.sub(r"\s+", " ", desc).strip()[:900]
    print("DESC:", desc)
    for v in (m.get("modelVersions") or [])[:4]:
        words = v.get("trainedWords") or []
        print(f"  VER {v.get('name')} base={v.get('baseModel')} triggers={words}")
        vd = re.sub(r"<[^>]+>", " ", v.get("description") or "")
        vd = re.sub(r"\s+", " ", vd).strip()[:500]
        if vd:
            print("   vdesc:", vd)
        # top review-ish: stats
        print("   stats:", v.get("stats"))


# Search then fetch details for promising hits
queries = [
    "Oral Insertion WAN 2.2",
    "Ultimate DeepThroat K3NK",
    "k3nk4llinon3 wan",
    "wan 2.2 cumshot i2v",
    "wan22 facial cum",
    "wan 2.2 ahegao cum",
    "wan22 cum in mouth",
]
seen = set()
for q in queries:
    data = get(
        "https://civitai.com/api/v1/models?"
        + urllib.parse.urlencode({"query": q, "limit": 10, "nsfw": "true"})
    )
    print("\n### SEARCH", q)
    for item in data.get("items") or []:
        mid = item["id"]
        name = item.get("name")
        print(f"  {mid}: {name}")
        if mid not in seen and any(
            x in (name or "").lower()
            for x in ("oral", "deep", "cum", "facial", "blow", "k3nk", "insertion")
        ):
            seen.add(mid)

# Always fetch the ones we already use / likely matches
priority = []
# resolve oral insertion + deepthroat by exact-ish search first result ids collected
for q, want in [
    ("Oral Insertion WAN 2.2", "oral insertion"),
    ("Ultimate DeepThroat K3NK", "deepthroat"),
    ("k3nk4llinon3", "k3nk"),
]:
    data = get(
        "https://civitai.com/api/v1/models?"
        + urllib.parse.urlencode({"query": q, "limit": 5, "nsfw": "true"})
    )
    for item in data.get("items") or []:
        if want in (item.get("name") or "").lower() or q.lower().split()[0] in (
            item.get("name") or ""
        ).lower():
            priority.append(item["id"])
            break

for mid in list(dict.fromkeys(priority + list(seen)))[:12]:
    try:
        show_model(mid)
    except Exception as exc:
        print("fail", mid, exc)

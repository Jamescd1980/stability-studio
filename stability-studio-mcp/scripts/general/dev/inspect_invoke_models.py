"""One-off: list InvokeAI registered models from local SQLite DB."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
from _bootstrap import ROOT  # noqa: E402

from studio.config import load_config  # noqa: E402


def main() -> None:
    cfg = load_config()
    default_db = (
        Path(cfg["stability_matrix"]["packages"]["comfyui"]).parents[1]
        / "InvokeAI"
        / "invokeai-root"
        / "databases"
        / "invokeai.db"
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=default_db, help="invokeai.db path")
    args = parser.parse_args()

    db = args.db
    if not db.is_file():
        print("invokeai.db not found:", db)
        return

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    print("tables:", tables)

    for table in tables:
        if "model" not in table.lower():
            continue
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        print(f"\n## {table}")
        print("columns:", cols)
        rows = cur.execute(f"SELECT * FROM {table}").fetchall()
        print(f"row count: {len(rows)}")
        for row in rows:
            d = dict(row)
            for k, v in list(d.items()):
                if isinstance(v, (bytes, bytearray)) or (isinstance(v, str) and len(v) > 200):
                    d[k] = f"<{type(v).__name__} len={len(v) if v else 0}>"
            print(json.dumps(d, indent=2, default=str))


if __name__ == "__main__":
    main()

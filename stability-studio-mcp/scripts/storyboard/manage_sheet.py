#!/usr/bin/env python3
"""Spreadsheet storyboard CLI — init, validate, queue, export Ren'Py."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.config import load_config  # noqa: E402
from studio.storyboard_cli import resolve_project_dir  # noqa: E402
from studio.storyboard_sheet import (  # noqa: E402
    SHEET_COLUMNS,
    export_renpy_skeleton,
    init_chapter_sheet,
    load_sheet,
    rows_needing_generation,
    sheet_path,
    validate_sheet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="VN storyboard spreadsheet tool")
    parser.add_argument("--project-dir", default="", help="Delivery project root")
    parser.add_argument("--chapter", type=int, default=1)
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create chapter CSV template")
    p_init.add_argument("--title", default="")
    p_init.set_defaults(cmd="init")

    sub.add_parser("columns", help="Print CSV column schema").set_defaults(cmd="columns")

    p_check = sub.add_parser("check", help="Validate sheet + asset paths")
    p_check.add_argument("--strict", action="store_true")
    p_check.set_defaults(cmd="check")

    p_queue = sub.add_parser("queue", help="List rows ready for MCP generation")
    p_queue.set_defaults(cmd="queue")

    p_renpy = sub.add_parser("export-renpy", help="Write Ren'Py skeleton under renpy/generated/")
    p_renpy.add_argument("--game-name", default="vn_game")
    p_renpy.set_defaults(cmd="renpy")

    args = parser.parse_args()
    project = resolve_project_dir(args.project_dir or None)

    try:
        if args.cmd == "columns":
            print(json.dumps({"columns": list(SHEET_COLUMNS)}, indent=2))
            return 0

        if args.cmd == "init":
            path = init_chapter_sheet(project, chapter=args.chapter, title=args.title)
            print(json.dumps({"status": "ok", "sheet": str(path)}, indent=2))
            return 0

        path = sheet_path(project, args.chapter)
        if args.cmd == "check":
            report = validate_sheet(project, path, strict=args.strict)
            print(json.dumps(report, indent=2))
            return 0 if report["ready"] else 1

        if args.cmd == "queue":
            rows, meta = load_sheet(path)
            queue = rows_needing_generation(rows)
            print(json.dumps({"sheet": str(path), "meta": meta, "queue": queue}, indent=2))
            return 0

        if args.cmd == "renpy":
            result = export_renpy_skeleton(
                project, path, chapter=args.chapter, game_name=args.game_name
            )
            print(json.dumps(result, indent=2))
            return 0

        return 1
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

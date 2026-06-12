#!/usr/bin/env python3
"""Storyboard CLI — plan, check, splice (see studio/storyboard_cli.py)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from studio.storyboard_cli import (  # noqa: E402
    run_check,
    run_plan,
    run_splice,
    storyboard_arg_parser,
)


def main() -> int:
    parser = storyboard_arg_parser("Storyboard pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Build manifest from a beat script (no GPU)")
    p_plan.add_argument("--title", default="storyboard")
    p_plan.add_argument("--script", default="")
    p_plan.add_argument("--script-file", default="")
    p_plan.add_argument("--hero-image", default="")
    p_plan.add_argument("--food-group", default="anime")
    p_plan.add_argument("--voice-instruction", default="")
    p_plan.add_argument("--lipsync", action="store_true")
    p_plan.add_argument("--fade-last", action="store_true")
    p_plan.add_argument("--clip-template", default="")
    p_plan.set_defaults(cmd="plan")

    p_check = sub.add_parser("check", help="Validate manifest success criteria")
    p_check.add_argument("--strict", action="store_true")
    p_check.set_defaults(cmd="check")

    p_status = sub.add_parser("status", help="Alias for check")
    p_status.add_argument("--strict", action="store_true")
    p_status.set_defaults(cmd="check")

    p_splice = sub.add_parser("splice", help="ffmpeg splice from manifest")
    p_splice.add_argument("--skip-missing", action="store_true")
    p_splice.set_defaults(cmd="splice")

    args = parser.parse_args()
    project_dir = args.project_dir or None

    try:
        if args.cmd == "plan":
            result = run_plan(
                project_dir=project_dir,
                manifest_name=args.manifest,
                script=args.script,
                script_file=args.script_file,
                title=args.title,
                hero_image=args.hero_image,
                food_group=args.food_group,
                voice_instruction=args.voice_instruction,
                lipsync=args.lipsync,
                fade_last=args.fade_last,
                clip_template=args.clip_template,
            )
            print(json.dumps(result, indent=2))
            return 0

        if args.cmd == "check":
            report = run_check(
                project_dir=project_dir,
                manifest_name=args.manifest,
                strict=args.strict,
            )
            print(json.dumps(report, indent=2))
            return 0 if report["ready"] else 1

        code, payload = run_splice(
            project_dir=project_dir,
            manifest_name=args.manifest,
            skip_missing=args.skip_missing,
        )
        stream = sys.stdout if code == 0 else sys.stderr
        print(json.dumps(payload, indent=2), file=stream)
        return code
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

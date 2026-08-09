"""CLI for PF05 strategy-bias validation using a CSV research panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .strategy_validation import (
    ValidationContractError,
    validate_lookahead,
    validate_recursive_stability,
    validate_strategy_bias_suite,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 02 PF05 strategy validator")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("lookahead", "recursive", "suite"):
        item = sub.add_parser(name)
        item.add_argument("--csv", required=True, type=Path)
        item.add_argument("--decision-date", action="append", required=True)
        item.add_argument("--output", type=Path)
        if name in {"recursive", "suite"}:
            item.add_argument("--warmup", type=int, action="append", default=None)
    return parser


def main() -> int:
    args = _parser().parse_args()
    frame = pd.read_csv(args.csv)
    dates = args.decision_date
    try:
        if args.command == "lookahead":
            payload = validate_lookahead(frame, decision_dates=dates).to_dict()
        elif args.command == "recursive":
            payload = validate_recursive_stability(
                frame,
                decision_dates=dates,
                warmup_sessions=tuple(args.warmup or (300, 320, 360)),
            ).to_dict()
        else:
            payload = validate_strategy_bias_suite(
                frame,
                decision_dates=dates,
                warmup_sessions=tuple(args.warmup or (300, 320, 360)),
            )
    except ValidationContractError as exc:
        payload = {"status": "ERROR", "error": str(exc)}
        code = 2
    else:
        code = 0 if payload.get("status") == "PASS" else 1

    raw = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(raw + "\n", encoding="utf-8")
    print(raw)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

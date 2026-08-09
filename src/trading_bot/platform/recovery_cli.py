"""Local PF10 fixture evidence CLI."""
from __future__ import annotations
import argparse, json
from datetime import datetime
from trading_bot.platform.recovery import build_pf10_fixture_recovery_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Render deterministic PF10 recovery fixture evidence")
    parser.add_argument("--as-of", required=True, help="ISO-8601 aware timestamp")
    args = parser.parse_args()
    report = build_pf10_fixture_recovery_report(as_of=datetime.fromisoformat(args.as_of))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

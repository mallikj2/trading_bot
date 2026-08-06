"""Credential-aware Phase 02 provider trial entrypoint."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from .massive import MassiveClient
from .sec_edgar import SecEdgarClient

UTC = timezone.utc


def environment_status() -> dict[str, Any]:
    massive = bool(os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY"))
    sec_user_agent = os.getenv("SEC_USER_AGENT")
    return {
        "massive_credentials": "AVAILABLE" if massive else "MISSING",
        "sec_user_agent": "AVAILABLE" if sec_user_agent and "@" in sec_user_agent else "MISSING",
        "credentialed_trial_ready": bool(massive and sec_user_agent and "@" in sec_user_agent),
    }


def run_smoke_trial(*, ticker: str, cik: str, as_of_date: date) -> dict[str, Any]:
    status = environment_status()
    result: dict[str, Any] = {
        "run_at": datetime.now(tz=UTC).isoformat(),
        "ticker": ticker,
        "cik": cik,
        "as_of_date": as_of_date.isoformat(),
        "environment": status,
        "checks": [],
    }
    if status["massive_credentials"] == "AVAILABLE":
        massive = MassiveClient()
        ticker_payload = massive.ticker_overview(ticker, as_of_date=as_of_date)
        result["checks"].append(
            {
                "id": "MASSIVE_TICKER_OVERVIEW",
                "status": "PASS",
                "request_id": ticker_payload.get("request_id"),
            }
        )
    else:
        result["checks"].append(
            {"id": "MASSIVE_TICKER_OVERVIEW", "status": "BLOCKED", "reason": "MASSIVE_API_KEY missing"}
        )

    if status["sec_user_agent"] == "AVAILABLE":
        sec = SecEdgarClient()
        submissions = sec.submissions(cik)
        companyfacts = sec.companyfacts(cik)
        result["checks"].append(
            {
                "id": "SEC_SUBMISSIONS_COMPANYFACTS",
                "status": "PASS",
                "submissions_cik": submissions.get("cik"),
                "companyfacts_cik": companyfacts.get("cik"),
            }
        )
    else:
        result["checks"].append(
            {"id": "SEC_SUBMISSIONS_COMPANYFACTS", "status": "BLOCKED", "reason": "SEC_USER_AGENT missing"}
        )
    result["status"] = "PASS" if all(item["status"] == "PASS" for item in result["checks"]) else "BLOCKED"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("environment-status")
    smoke = subparsers.add_parser("smoke")
    smoke.add_argument("--ticker", default="AAPL")
    smoke.add_argument("--cik", default="0000320193")
    smoke.add_argument("--as-of-date", type=date.fromisoformat, default=date(2025, 12, 31))
    smoke.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.command == "environment-status":
        print(json.dumps(environment_status(), indent=2, sort_keys=True))
        return 0

    payload = run_smoke_trial(ticker=args.ticker, cik=args.cik, as_of_date=args.as_of_date)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

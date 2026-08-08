"""Credentialed PIT security-master and exact-execution companion trial.

This runner is intentionally independent of the Kibot EOD smoke test.  It will
not perform a Databento request unless credentials, research-license approval,
an explicit execution dataset, and a separately approved execution-coverage
profile are all present.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .databento_companion import (
    DatabentoCompanionClient,
    exact_trade_vwap,
    find_ticker_reuse,
    normalize_security_master,
    normalize_trades,
    select_primary_listing_as_of,
)

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")


def _approved(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def environment_status() -> dict[str, Any]:
    dataset = (
        os.getenv("DATABENTO_EXECUTION_DATASET", "").strip()
        or os.getenv("DATABENTO_US_EQUITIES_DATASET", "").strip()
    )
    credentials = bool(os.getenv("DATABENTO_API_KEY"))
    license_approved = _approved(os.getenv("DATABENTO_RESEARCH_LICENSE_APPROVED"))
    coverage_approved = _approved(os.getenv("DATABENTO_EXECUTION_COVERAGE_APPROVED"))
    return {
        "provider": "DATABENTO",
        "credentials": "AVAILABLE" if credentials else "MISSING",
        "research_license_approved": "YES" if license_approved else "NO",
        "execution_dataset": dataset or "MISSING",
        "execution_coverage_approved": "YES" if coverage_approved else "NO",
        "trial_ready": bool(credentials and license_approved and dataset and coverage_approved),
    }


def run_smoke(*, ticker: str, as_of_date: date) -> dict[str, Any]:
    status = environment_status()
    payload: dict[str, Any] = {
        "version": "0.2.0",
        "run_at": datetime.now(tz=UTC).isoformat(),
        "ticker": ticker.upper(),
        "as_of_date": as_of_date.isoformat(),
        "environment": status,
        "checks": [],
    }
    if not status["trial_ready"]:
        payload["checks"].append(
            {
                "id": "PIT_SECURITY_MASTER_AND_EXACT_EXECUTION_SMOKE",
                "status": "BLOCKED",
                "reason": (
                    "DATABENTO_API_KEY, DATABENTO_RESEARCH_LICENSE_APPROVED=true, "
                    "DATABENTO_EXECUTION_DATASET, and "
                    "DATABENTO_EXECUTION_COVERAGE_APPROVED=true are required"
                ),
            }
        )
        payload["status"] = "BLOCKED"
        return payload

    try:
        client = DatabentoCompanionClient()
        raw = client.security_master_range(
            symbol=ticker.upper(),
            start=as_of_date - timedelta(days=14),
            end=as_of_date + timedelta(days=2),
        )
        listings = normalize_security_master(raw, source_snapshot_id="credentialed-pit-companion-smoke")
        ticker_reuse = find_ticker_reuse(listings)
        candidate_ids = sorted(
            {
                row.instrument_id
                for row in listings
                if ticker.upper() in {(row.symbol or "").upper(), (row.nasdaq_symbol or "").upper()}
            },
            key=lambda item: item.hex,
        )
        if len(candidate_ids) != 1:
            raise ValueError("smoke symbol did not resolve to exactly one provider security")
        decision_at = datetime.combine(as_of_date, time(16, 30), tzinfo=NEW_YORK)
        listing = select_primary_listing_as_of(
            listings,
            instrument_id=candidate_ids[0],
            decision_at=decision_at,
        )
        if not listing.figi:
            raise ValueError("PIT primary listing lacks FIGI for stable historical trade query")
        if not listing.cik:
            raise ValueError("PIT primary listing lacks CIK required for SEC sector ledger")

        window_start = datetime.combine(as_of_date, time(10, 0), tzinfo=NEW_YORK).astimezone(UTC)
        window_end = datetime.combine(as_of_date, time(10, 30), tzinfo=NEW_YORK).astimezone(UTC)
        raw_trades = client.historical_trades(
            dataset=str(status["execution_dataset"]),
            symbol=listing.figi,
            stype_in="figi",
            start=window_start,
            end=window_end,
        )
        trades = normalize_trades(raw_trades)
        vwap = exact_trade_vwap(trades, session_date=as_of_date)
        payload["checks"].append(
            {
                "id": "PIT_SECURITY_MASTER",
                "status": "PASS",
                "listing_id": listing.provider_listing_id,
                "security_id": listing.provider_security_id,
                "figi": listing.figi,
                "cik": listing.cik,
                "exchange": listing.exchange,
                "security_type": listing.security_type.value,
                "listing_state": listing.listing_state.value,
                "effective_at": listing.effective_at.isoformat(),
                "available_at": listing.available_at.isoformat(),
                "ticker_reuse_in_response": ticker_reuse,
            }
        )
        payload["checks"].append(
            {
                "id": "EXACT_EXECUTION_WINDOW",
                "status": "PASS",
                "dataset": status["execution_dataset"],
                "window_start_utc": window_start.isoformat(),
                "window_end_utc": window_end.isoformat(),
                "trade_count": vwap.trade_count,
                "volume": vwap.total_volume,
                "vwap": str(vwap.vwap),
            }
        )
        payload["status"] = "PASS"
    except Exception as exc:  # credentialed evidence must never become a false pass
        payload["checks"].append(
            {
                "id": "PIT_SECURITY_MASTER_AND_EXACT_EXECUTION_SMOKE",
                "status": "FAIL",
                "reason": type(exc).__name__,
                "detail": str(exc),
            }
        )
        payload["status"] = "FAIL"
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("environment-status")
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--ticker", default="AAPL")
    smoke.add_argument("--as-of-date", type=date.fromisoformat, default=date(2025, 12, 31))
    smoke.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "environment-status":
        print(json.dumps(environment_status(), indent=2, sort_keys=True))
        return 0
    result = run_smoke(ticker=args.ticker, as_of_date=args.as_of_date)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

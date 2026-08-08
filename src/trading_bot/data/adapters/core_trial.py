"""Core research-provider and PIT companion trial for Phase 02."""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .kibot import KibotClient, parse_daily_history, parse_adjustments
from .databento_companion import (
    DatabentoCompanionClient,
    dataframe_row_count,
    exact_trade_vwap,
    normalize_security_master,
    normalize_trades,
    select_primary_listing_as_of,
)
from .sec_edgar import SecEdgarClient

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")


def _approved(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def environment_status() -> dict[str, Any]:
    kibot_credentials = bool(os.getenv("KIBOT_USERNAME") and os.getenv("KIBOT_PASSWORD"))
    kibot_license = _approved(os.getenv("KIBOT_PRIVATE_RESEARCH_LICENSE_APPROVED"))
    databento_credentials = bool(os.getenv("DATABENTO_API_KEY"))
    databento_license = _approved(os.getenv("DATABENTO_RESEARCH_LICENSE_APPROVED"))
    databento_dataset = (
        os.getenv("DATABENTO_EXECUTION_DATASET", "").strip()
        or os.getenv("DATABENTO_US_EQUITIES_DATASET", "").strip()
    )
    databento_execution_coverage = _approved(os.getenv("DATABENTO_EXECUTION_COVERAGE_APPROVED"))
    sec_user_agent = os.getenv("SEC_USER_AGENT")
    sec_ready = bool(sec_user_agent and "@" in sec_user_agent)
    return {
        "selected_core_price_provider": "KIBOT",
        "selected_pit_security_master_candidate": "DATABENTO",
        "kibot_credentials": "AVAILABLE" if kibot_credentials else "MISSING",
        "kibot_private_research_license_acknowledged": "YES" if kibot_license else "NO",
        "databento_credentials": "AVAILABLE" if databento_credentials else "MISSING",
        "databento_research_license_acknowledged": "YES" if databento_license else "NO",
        "databento_execution_dataset": databento_dataset or "MISSING",
        "databento_execution_coverage_approved": "YES" if databento_execution_coverage else "NO",
        "sec_user_agent": "AVAILABLE" if sec_ready else "MISSING",
        "core_price_trial_ready": bool(kibot_credentials and kibot_license),
        "databento_companion_trial_ready": bool(
            databento_credentials
            and databento_license
            and databento_dataset
            and databento_execution_coverage
        ),
        "full_market_data_stack_trial_ready": bool(
            kibot_credentials
            and kibot_license
            and databento_credentials
            and databento_license
            and databento_dataset
            and databento_execution_coverage
            and sec_ready
        ),
    }


def run_kibot_smoke(*, ticker: str, as_of_date: date) -> dict[str, Any]:
    status = environment_status()
    result: dict[str, Any] = {
        "run_at": datetime.now(tz=UTC).isoformat(),
        "ticker": ticker,
        "as_of_date": as_of_date.isoformat(),
        "environment": status,
        "checks": [],
    }
    if not status["core_price_trial_ready"]:
        result["checks"].append({
            "id": "KIBOT_CORE_PRICE_SMOKE",
            "status": "BLOCKED",
            "reason": "KIBOT credentials and explicit private-research license acknowledgement are required",
        })
    else:
        client = KibotClient()
        history = client.history(ticker, interval="daily", start=as_of_date, end=as_of_date, unadjusted=True)
        bars = parse_daily_history(history)
        result["checks"].append({
            "id": "KIBOT_CORE_PRICE_SMOKE",
            "status": "PASS",
            "rows": len(bars),
            "session_date": bars[-1][0].isoformat(),
        })
        try:
            adjustment_text = client.adjustments(symbol=ticker)
            adjustments = parse_adjustments(adjustment_text)
            result["checks"].append({"id": "KIBOT_ADJUSTMENT_SCHEMA", "status": "PASS", "rows": len(adjustments)})
        except Exception as exc:  # evidence is recorded, never converted into a false pass
            result["checks"].append({"id": "KIBOT_ADJUSTMENT_SCHEMA", "status": "FAIL", "reason": type(exc).__name__})

    if status["sec_user_agent"] == "AVAILABLE":
        # AAPL CIK is fixed only for the smoke path. Representative testing uses
        # PIT identity from the approved security-master source.
        if ticker.upper() == "AAPL":
            sec = SecEdgarClient()
            submissions = sec.submissions("0000320193")
            result["checks"].append({"id": "SEC_SMOKE", "status": "PASS", "cik": submissions.get("cik")})
    else:
        result["checks"].append({"id": "SEC_SMOKE", "status": "BLOCKED", "reason": "SEC_USER_AGENT missing"})

    if not status["databento_companion_trial_ready"]:
        result["checks"].append({
            "id": "DATABENTO_PIT_IDENTITY_EXECUTION_SMOKE",
            "status": "BLOCKED",
            "reason": (
                "Databento API key, research-license approval, an explicit execution dataset, "
                "and execution-coverage approval are required"
            ),
        })
    else:
        try:
            companion = DatabentoCompanionClient()
            # Query around the date and then enforce provider record-time availability.
            security_master_raw = companion.security_master_range(
                symbol=ticker,
                start=as_of_date - timedelta(days=7),
                end=as_of_date + timedelta(days=2),
            )
            security_master = normalize_security_master(
                security_master_raw,
                source_snapshot_id="credentialed-smoke-security-master",
            )
            candidate_ids = sorted({row.instrument_id for row in security_master if (row.symbol or row.nasdaq_symbol) == ticker})
            if len(candidate_ids) != 1:
                raise ValueError("smoke ticker did not resolve to exactly one PIT provider security")
            decision_at = datetime.combine(as_of_date, time(16, 30), tzinfo=NEW_YORK)
            listing = select_primary_listing_as_of(
                security_master,
                instrument_id=candidate_ids[0],
                decision_at=decision_at,
            )
            if not listing.figi:
                raise ValueError("PIT listing lacks FIGI required for stable execution query")

            start_local = datetime.combine(as_of_date, time(10, 0), tzinfo=NEW_YORK)
            end_local = datetime.combine(as_of_date, time(10, 30), tzinfo=NEW_YORK)
            trades_raw = companion.historical_trades(
                dataset=str(status["databento_execution_dataset"]),
                symbol=listing.figi,
                stype_in="figi",
                start=start_local.astimezone(UTC),
                end=end_local.astimezone(UTC),
            )
            trades = normalize_trades(trades_raw)
            vwap = exact_trade_vwap(trades, session_date=as_of_date)
            result["checks"].append({
                "id": "DATABENTO_PIT_IDENTITY_EXECUTION_SMOKE",
                "status": "PASS",
                "security_master_rows": dataframe_row_count(security_master_raw),
                "trade_rows": len(trades),
                "figi": listing.figi,
                "cik": listing.cik,
                "exchange": listing.exchange,
                "vwap": str(vwap.vwap),
                "vwap_trade_count": vwap.trade_count,
                "vwap_volume": vwap.total_volume,
            })
        except Exception as exc:
            result["checks"].append({
                "id": "DATABENTO_PIT_IDENTITY_EXECUTION_SMOKE",
                "status": "FAIL",
                "reason": type(exc).__name__,
                "detail": str(exc),
            })

    result["status"] = "PASS" if result["checks"] and all(x["status"] == "PASS" for x in result["checks"]) else "BLOCKED"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("environment-status")
    smoke = sub.add_parser("kibot-smoke")
    smoke.add_argument("--ticker", default="AAPL")
    smoke.add_argument("--as-of-date", type=date.fromisoformat, default=date(2025, 12, 31))
    smoke.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "environment-status":
        print(json.dumps(environment_status(), indent=2, sort_keys=True))
        return 0
    payload = run_kibot_smoke(ticker=args.ticker, as_of_date=args.as_of_date)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

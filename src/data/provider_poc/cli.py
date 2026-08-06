from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from .adapters.massive import MassiveClient
from .adapters.sec_edgar import SecEdgarClient
from .validators import (
    validate_earnings_revisions,
    validate_intraday_vwap_window,
    validate_ticker_snapshot,
)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_fixtures(root: Path) -> int:
    tickers = json.loads((root / "ticker_snapshot.json").read_text(encoding="utf-8"))
    validate_ticker_snapshot(tickers, as_of_date=date.fromisoformat("2024-11-29"))

    bars = json.loads((root / "intraday_complete.json").read_text(encoding="utf-8"))
    result = validate_intraday_vwap_window(
        bars,
        symbol="TEST",
        session_date=date.fromisoformat("2024-11-29"),
    )

    earnings = json.loads((root / "earnings_revisions.json").read_text(encoding="utf-8"))
    validate_earnings_revisions(earnings)
    print(json.dumps({"status": "PASS", "vwap": result.vwap}, indent=2))
    return 0


def massive_smoke(args: argparse.Namespace) -> int:
    client = MassiveClient()
    output = Path(args.output)
    symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]

    payload = client.get_json(
        "/v3/reference/tickers",
        {"date": args.as_of_date, "active": "true", "market": "stocks", "limit": 1000},
    )
    raw_path = output / f"tickers_{args.as_of_date}.json"
    client.save_raw(payload, raw_path)
    print(f"saved {raw_path} sha256={_hash_file(raw_path)}")

    for symbol in symbols:
        details = client.get_json(f"/v3/reference/tickers/{symbol}", {"date": args.as_of_date})
        detail_path = output / f"ticker_{symbol}_{args.as_of_date}.json"
        client.save_raw(details, detail_path)
        print(f"saved {detail_path} sha256={_hash_file(detail_path)}")
    return 0


def massive_window(args: argparse.Namespace) -> int:
    client = MassiveClient()
    payload = client.get_json(
        f"/v2/aggs/ticker/{args.symbol}/range/5/minute/{args.session_date}/{args.session_date}",
        {"adjusted": "false", "sort": "asc", "limit": 50000},
    )
    output = Path(args.output) / f"window_{args.symbol}_{args.session_date}.json"
    client.save_raw(payload, output)
    result = validate_intraday_vwap_window(
        payload.get("results", []),
        symbol=args.symbol,
        session_date=date.fromisoformat(args.session_date),
    )
    print(json.dumps(asdict(result), indent=2, default=str))
    print(f"sha256={_hash_file(output)}")
    return 0


def sec_smoke(args: argparse.Namespace) -> int:
    client = SecEdgarClient()
    output = Path(args.output)
    submissions = client.submissions(args.cik)
    facts = client.companyfacts(args.cik)
    sub_path = output / f"CIK{int(args.cik):010d}_submissions.json"
    fact_path = output / f"CIK{int(args.cik):010d}_companyfacts.json"
    client.save_raw(submissions, sub_path)
    client.save_raw(facts, fact_path)
    print(f"decision_at={datetime.fromisoformat(args.decision_at.replace('Z', '+00:00')).isoformat()}")
    print(f"submissions_sha256={_hash_file(sub_path)}")
    print(f"companyfacts_sha256={_hash_file(fact_path)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 02 provider PoC")
    commands = parser.add_subparsers(dest="command", required=True)

    fixture = commands.add_parser("validate-fixtures")
    fixture.add_argument("--fixture-root", type=Path, required=True)
    fixture.set_defaults(func=lambda args: validate_fixtures(args.fixture_root))

    smoke = commands.add_parser("massive-smoke")
    smoke.add_argument("--as-of-date", required=True)
    smoke.add_argument("--symbols", required=True)
    smoke.add_argument("--output", required=True)
    smoke.set_defaults(func=massive_smoke)

    window = commands.add_parser("massive-window")
    window.add_argument("--symbol", required=True)
    window.add_argument("--session-date", required=True)
    window.add_argument("--output", required=True)
    window.set_defaults(func=massive_window)

    sec = commands.add_parser("sec-smoke")
    sec.add_argument("--cik", required=True)
    sec.add_argument("--decision-at", required=True)
    sec.add_argument("--output", required=True)
    sec.set_defaults(func=sec_smoke)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

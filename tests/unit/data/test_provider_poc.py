from __future__ import annotations

import json
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.data.provider_poc.validators import (  # noqa: E402
    ValidationError,
    conservative_corwin_schultz_bps,
    select_pit_record,
    validate_earnings_revisions,
    validate_intraday_vwap_window,
    validate_ticker_snapshot,
)

FIXTURES = ROOT / "tests" / "fixtures" / "provider_poc"
UTC = timezone.utc


class ProviderPocTests(unittest.TestCase):
    def load(self, name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_ticker_snapshot_passes(self) -> None:
        validate_ticker_snapshot(
            self.load("ticker_snapshot.json"),
            as_of_date=date(2024, 11, 29),
        )

    def test_ticker_snapshot_rejects_non_common_stock(self) -> None:
        rows = self.load("ticker_snapshot.json")
        rows[0]["type"] = "ETF"
        with self.assertRaises(ValidationError):
            validate_ticker_snapshot(rows, as_of_date=date(2024, 11, 29))

    def test_ticker_snapshot_requires_stable_identity(self) -> None:
        rows = self.load("ticker_snapshot.json")
        rows[0]["share_class_figi"] = None
        rows[0]["composite_figi"] = None
        rows[0]["cik"] = None
        with self.assertRaises(ValidationError):
            validate_ticker_snapshot(rows, as_of_date=date(2024, 11, 29))

    def test_complete_vwap_window(self) -> None:
        result = validate_intraday_vwap_window(
            self.load("intraday_complete.json"),
            symbol="TEST",
            session_date=date(2024, 11, 29),
        )
        self.assertEqual(result.interval_count, 6)
        self.assertEqual(result.total_volume, 7500)
        self.assertAlmostEqual(result.vwap, 100.1366666667, places=8)

    def test_incomplete_vwap_window_fails(self) -> None:
        with self.assertRaises(ValidationError):
            validate_intraday_vwap_window(
                self.load("intraday_incomplete.json"),
                symbol="TEST",
                session_date=date(2024, 11, 29),
            )

    def test_zero_volume_vwap_window_fails(self) -> None:
        rows = self.load("intraday_complete.json")
        rows[2]["v"] = 0
        with self.assertRaises(ValidationError):
            validate_intraday_vwap_window(
                rows,
                symbol="TEST",
                session_date=date(2024, 11, 29),
            )

    def test_future_pit_record_is_invisible(self) -> None:
        rows = self.load("pit_records.json")
        selected = select_pit_record(
            rows,
            decision_at=datetime(2024, 6, 1, tzinfo=UTC),
        )
        self.assertEqual(selected["value"], 100)

    def test_latest_known_pit_revision_is_selected(self) -> None:
        rows = self.load("pit_records.json")
        selected = select_pit_record(
            rows,
            decision_at=datetime(2024, 9, 1, tzinfo=UTC),
        )
        self.assertEqual(selected["value"], 80)

    def test_no_known_pit_record_fails(self) -> None:
        with self.assertRaises(ValidationError):
            select_pit_record(
                self.load("pit_records.json"),
                decision_at=datetime(2024, 1, 1, tzinfo=UTC),
            )

    def test_earnings_revision_sequence_passes(self) -> None:
        validate_earnings_revisions(self.load("earnings_revisions.json"))

    def test_current_only_earnings_calendar_fails(self) -> None:
        with self.assertRaises(ValidationError):
            validate_earnings_revisions([self.load("earnings_revisions.json")[-1]])

    def test_spread_proxy_has_floor(self) -> None:
        spread = conservative_corwin_schultz_bps(
            high_t=100.1,
            low_t=100.0,
            high_prev=100.1,
            low_prev=100.0,
        )
        self.assertGreaterEqual(spread, 5.0)

    def test_spread_proxy_rejects_invalid_bar(self) -> None:
        with self.assertRaises(ValidationError):
            conservative_corwin_schultz_bps(
                high_t=99,
                low_t=100,
                high_prev=101,
                low_prev=100,
            )

    def test_spread_proxy_is_deterministic(self) -> None:
        args = dict(high_t=101.5, low_t=99.5, high_prev=101.0, low_prev=99.0)
        self.assertEqual(
            conservative_corwin_schultz_bps(**args),
            conservative_corwin_schultz_bps(**args),
        )


if __name__ == "__main__":
    unittest.main()

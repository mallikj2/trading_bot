from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from trading_bot.data.contracts import Instrument, SecurityType, SymbolAlias  # noqa: E402
from trading_bot.data.errors import IdentityConflictError, PointInTimeError  # noqa: E402
from trading_bot.data.identity import InstrumentMaster  # noqa: E402
from trading_bot.data.pit import derive_feature_available_at, select_latest_known  # noqa: E402

UTC = timezone.utc


@dataclass(frozen=True)
class Record:
    value: int
    available_at: datetime
    revision: int


class PointInTimeAndIdentityTests(unittest.TestCase):
    def test_future_revision_is_invisible(self) -> None:
        rows = [
            Record(100, datetime(2024, 5, 1, tzinfo=UTC), 0),
            Record(80, datetime(2024, 8, 1, tzinfo=UTC), 1),
        ]
        selected = select_latest_known(rows, decision_at=datetime(2024, 6, 1, tzinfo=UTC))
        self.assertEqual(selected.value, 100)

    def test_latest_known_revision_selected(self) -> None:
        rows = [
            Record(100, datetime(2024, 5, 1, tzinfo=UTC), 0),
            Record(80, datetime(2024, 8, 1, tzinfo=UTC), 1),
        ]
        selected = select_latest_known(rows, decision_at=datetime(2024, 9, 1, tzinfo=UTC))
        self.assertEqual(selected.value, 80)

    def test_no_future_fallback(self) -> None:
        with self.assertRaises(PointInTimeError):
            select_latest_known(
                [Record(100, datetime(2024, 5, 1, tzinfo=UTC), 0)],
                decision_at=datetime(2024, 4, 1, tzinfo=UTC),
            )

    def test_feature_availability_uses_latest_input(self) -> None:
        result = derive_feature_available_at(
            [datetime(2024, 5, 1, tzinfo=UTC), datetime(2024, 5, 2, tzinfo=UTC)],
            processing_latency=timedelta(minutes=3),
        )
        self.assertEqual(result, datetime(2024, 5, 2, 0, 3, tzinfo=UTC))

    def make_instrument(self):
        return Instrument(
            instrument_id=uuid4(),
            security_type=SecurityType.COMMON_STOCK,
            currency="USD",
            country_of_listing="US",
            created_at=datetime(2000, 1, 1, tzinfo=UTC),
        )

    def test_symbol_change_preserves_identity(self) -> None:
        master = InstrumentMaster()
        instrument = self.make_instrument()
        master.add_instrument(instrument)
        master.add_alias(
            SymbolAlias(
                instrument_id=instrument.instrument_id,
                symbol="OLD",
                exchange="NASDAQ",
                valid_from=datetime(2020, 1, 1, tzinfo=UTC),
                valid_to=datetime(2024, 1, 1, tzinfo=UTC),
                provider_symbol="OLD",
                source_snapshot_id="s1",
                mapping_reason="SYMBOL_CHANGE",
                available_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        master.add_alias(
            SymbolAlias(
                instrument_id=instrument.instrument_id,
                symbol="NEW",
                exchange="NASDAQ",
                valid_from=datetime(2024, 1, 1, tzinfo=UTC),
                valid_to=None,
                provider_symbol="NEW",
                source_snapshot_id="s2",
                mapping_reason="SYMBOL_CHANGE",
                available_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )
        self.assertEqual(
            master.resolve(symbol="OLD", exchange="NASDAQ", at=datetime(2023, 6, 1, tzinfo=UTC)),
            instrument.instrument_id,
        )
        self.assertEqual(
            master.resolve(symbol="NEW", exchange="NASDAQ", at=datetime(2024, 6, 1, tzinfo=UTC)),
            instrument.instrument_id,
        )

    def test_nonoverlapping_ticker_reuse_is_allowed(self) -> None:
        master = InstrumentMaster()
        first = self.make_instrument()
        second = self.make_instrument()
        master.add_instrument(first)
        master.add_instrument(second)
        master.add_alias(SymbolAlias(first.instrument_id, "ABC", "NYSE", datetime(2000, 1, 1, tzinfo=UTC), datetime(2010, 1, 1, tzinfo=UTC), "ABC", "s1", "DELISTING", datetime(2000, 1, 1, tzinfo=UTC)))
        master.add_alias(SymbolAlias(second.instrument_id, "ABC", "NYSE", datetime(2015, 1, 1, tzinfo=UTC), None, "ABC", "s2", "NEW_LISTING", datetime(2015, 1, 1, tzinfo=UTC)))
        self.assertEqual(master.resolve(symbol="ABC", exchange="NYSE", at=datetime(2005, 1, 1, tzinfo=UTC)), first.instrument_id)
        self.assertEqual(master.resolve(symbol="ABC", exchange="NYSE", at=datetime(2020, 1, 1, tzinfo=UTC)), second.instrument_id)

    def test_overlapping_ticker_ownership_rejected(self) -> None:
        master = InstrumentMaster()
        first = self.make_instrument()
        second = self.make_instrument()
        master.add_instrument(first)
        master.add_instrument(second)
        master.add_alias(SymbolAlias(first.instrument_id, "ABC", "NYSE", datetime(2000, 1, 1, tzinfo=UTC), None, "ABC", "s1", "LISTING", datetime(2000, 1, 1, tzinfo=UTC)))
        with self.assertRaises(IdentityConflictError):
            master.add_alias(SymbolAlias(second.instrument_id, "ABC", "NYSE", datetime(2010, 1, 1, tzinfo=UTC), None, "ABC", "s2", "LISTING", datetime(2010, 1, 1, tzinfo=UTC)))

    def test_alias_not_known_by_decision_is_invisible(self) -> None:
        master = InstrumentMaster()
        instrument = self.make_instrument()
        master.add_instrument(instrument)
        master.add_alias(
            SymbolAlias(
                instrument.instrument_id,
                "NEW",
                "NASDAQ",
                datetime(2024, 1, 1, tzinfo=UTC),
                None,
                "NEW",
                "s1",
                "CORRECTION",
                datetime(2024, 6, 1, tzinfo=UTC),
            )
        )
        with self.assertRaises(IdentityConflictError):
            master.resolve(
                symbol="NEW",
                exchange="NASDAQ",
                at=datetime(2024, 3, 1, tzinfo=UTC),
                decision_at=datetime(2024, 3, 1, tzinfo=UTC),
            )

    def test_conflicting_latest_pit_records_fail(self) -> None:
        rows = [
            Record(100, datetime(2024, 5, 1, tzinfo=UTC), 1),
            Record(80, datetime(2024, 5, 1, tzinfo=UTC), 1),
        ]
        with self.assertRaises(PointInTimeError):
            select_latest_known(rows, decision_at=datetime(2024, 6, 1, tzinfo=UTC))


if __name__ == "__main__":
    unittest.main()

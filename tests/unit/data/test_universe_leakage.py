from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from trading_bot.data.contracts import (  # noqa: E402
    DataQualityStatus,
    ListingState,
    MarketCapObservation,
    SecurityType,
    UniverseInput,
    UniverseReason,
)
from trading_bot.data.errors import LeakageError, UniverseBuildError  # noqa: E402
from trading_bot.data.leakage import assert_lineage_hashes, assert_no_future_information  # noqa: E402
from trading_bot.data.universe import build_monthly_universe, universe_membership_hash  # noqa: E402

UTC = timezone.utc
FREEZE = datetime(2024, 6, 28, 20, 30, tzinfo=UTC)


def valid_input(**overrides) -> UniverseInput:
    values = dict(
        instrument_id=uuid4(),
        exchange="NYSE",
        security_type=SecurityType.COMMON_STOCK,
        listing_state=ListingState.LISTED,
        adjusted_close=Decimal("50"),
        market_cap=Decimal("5000000000"),
        adv60=Decimal("50000000"),
        valid_sessions=500,
        vol20_annualized=Decimal("0.25"),
        sector_code="D",
        quality_status=DataQualityStatus.VALID,
        unresolved_corporate_action=False,
        identity_resolved=True,
        latest_available_at=FREEZE,
        source_manifest_hashes=("a" * 64,),
    )
    values.update(overrides)
    return UniverseInput(**values)


class UniverseAndLeakageTests(unittest.TestCase):
    def build(self, rows):
        return build_monthly_universe(
            rows,
            effective_month=date(2024, 7, 1),
            freeze_at=FREEZE,
            source_manifest_hash="f" * 64,
            universe_version="2024-07-v1",
        )

    def test_valid_instrument_is_eligible(self) -> None:
        membership = self.build([valid_input()])[0]
        self.assertTrue(membership.eligible)
        self.assertEqual(membership.reason_codes, (UniverseReason.ELIGIBLE,))

    def test_all_failures_are_recorded_deterministically(self) -> None:
        row = valid_input(
            exchange="OTC",
            security_type=SecurityType.ETF,
            listing_state=ListingState.DELISTED,
            adjusted_close=Decimal("9.99"),
            market_cap=Decimal("1999999999"),
            adv60=Decimal("24999999"),
            valid_sessions=299,
            vol20_annualized=Decimal("0.81"),
            sector_code=None,
            quality_status=DataQualityStatus.SUSPECT,
            unresolved_corporate_action=True,
            identity_resolved=False,
        )
        membership = self.build([row])[0]
        self.assertFalse(membership.eligible)
        self.assertEqual(
            membership.reason_codes,
            (
                UniverseReason.UNKNOWN_IDENTITY,
                UniverseReason.WRONG_EXCHANGE,
                UniverseReason.WRONG_SECURITY_TYPE,
                UniverseReason.NOT_LISTED,
                UniverseReason.PRICE_TOO_LOW,
                UniverseReason.MARKET_CAP_TOO_LOW,
                UniverseReason.INSUFFICIENT_LIQUIDITY,
                UniverseReason.INSUFFICIENT_HISTORY,
                UniverseReason.VOLATILITY_TOO_HIGH,
                UniverseReason.MISSING_SECTOR,
                UniverseReason.DATA_QUALITY_FAILURE,
                UniverseReason.CORPORATE_ACTION_UNRESOLVED,
            ),
        )

    def test_future_input_is_excluded(self) -> None:
        membership = self.build([
            valid_input(latest_available_at=datetime(2024, 7, 1, tzinfo=UTC))
        ])[0]
        self.assertIn(UniverseReason.FUTURE_INFORMATION, membership.reason_codes)

    def test_boundary_values_are_inclusive(self) -> None:
        membership = self.build([
            valid_input(
                adjusted_close=Decimal("10"),
                market_cap=Decimal("2000000000"),
                adv60=Decimal("25000000"),
                valid_sessions=300,
                vol20_annualized=Decimal("0.80"),
            )
        ])[0]
        self.assertTrue(membership.eligible)

    def test_membership_hash_is_order_invariant(self) -> None:
        first = valid_input()
        second = valid_input()
        left = self.build([first, second])
        right = self.build([second, first])
        self.assertEqual(universe_membership_hash(left), universe_membership_hash(right))

    def test_duplicate_instrument_rejected(self) -> None:
        row = valid_input()
        with self.assertRaises(UniverseBuildError):
            self.build([row, row])

    def test_future_record_scan(self) -> None:
        rows = [
            MarketCapObservation(
                instrument_id=uuid4(),
                observed_at=datetime(2024, 6, 1, tzinfo=UTC),
                available_at=datetime(2024, 7, 1, tzinfo=UTC),
                market_cap=Decimal("5000000000"),
                source_snapshot_id="s1",
            )
        ]
        with self.assertRaises(LeakageError):
            assert_no_future_information(rows, decision_at=FREEZE)

    def test_lineage_hash_validation(self) -> None:
        assert_lineage_hashes(["a" * 64, "b" * 64])
        with self.assertRaises(LeakageError):
            assert_lineage_hashes(["not-a-hash"])


if __name__ == "__main__":
    unittest.main()

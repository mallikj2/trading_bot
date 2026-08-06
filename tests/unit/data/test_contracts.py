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
    CorporateAction,
    CorporateActionType,
    DailyBar,
    DataQualityStatus,
    FeatureObservation,
    SecurityType,
    UniverseMembership,
    UniverseReason,
)
from trading_bot.data.errors import DataContractError  # noqa: E402

UTC = timezone.utc


class ContractTests(unittest.TestCase):
    def test_valid_daily_bar(self) -> None:
        bar = DailyBar(
            instrument_id=uuid4(),
            session_date=date(2024, 11, 29),
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("101"),
            volume=1000,
            observed_at=datetime(2024, 11, 29, 18, 0, tzinfo=UTC),
            available_at=datetime(2024, 11, 29, 18, 15, tzinfo=UTC),
            snapshot_id="snapshot",
        )
        self.assertEqual(bar.quality_status, DataQualityStatus.VALID)

    def test_invalid_ohlc_rejected(self) -> None:
        with self.assertRaises(DataContractError):
            DailyBar(
                instrument_id=uuid4(),
                session_date=date(2024, 11, 29),
                open=Decimal("100"),
                high=Decimal("99"),
                low=Decimal("98"),
                close=Decimal("101"),
                volume=1000,
                observed_at=datetime(2024, 11, 29, 18, 0, tzinfo=UTC),
                available_at=datetime(2024, 11, 29, 18, 15, tzinfo=UTC),
                snapshot_id="snapshot",
            )

    def test_naive_datetime_rejected(self) -> None:
        with self.assertRaises(DataContractError):
            DailyBar(
                instrument_id=uuid4(),
                session_date=date(2024, 11, 29),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=1000,
                observed_at=datetime(2024, 11, 29, 18, 0),
                available_at=datetime(2024, 11, 29, 18, 15, tzinfo=UTC),
                snapshot_id="snapshot",
            )

    def test_split_requires_ratio(self) -> None:
        with self.assertRaises(DataContractError):
            CorporateAction(
                action_id="split-1",
                instrument_id=uuid4(),
                action_type=CorporateActionType.SPLIT,
                effective_at=datetime(2024, 6, 1, tzinfo=UTC),
                available_at=datetime(2024, 5, 1, tzinfo=UTC),
                source_snapshot_id="snapshot",
            )

    def test_null_feature_requires_reason(self) -> None:
        with self.assertRaises(DataContractError):
            FeatureObservation(
                feature_name="mom_12_1",
                feature_version="1",
                instrument_id=uuid4(),
                observed_at=datetime(2024, 6, 1, tzinfo=UTC),
                available_at=datetime(2024, 6, 1, tzinfo=UTC),
                value=None,
                input_manifest_hashes=("a" * 64,),
                formula_hash="b" * 64,
            )

    def test_membership_invariant(self) -> None:
        with self.assertRaises(DataContractError):
            UniverseMembership(
                universe_version="u1",
                effective_month=date(2024, 7, 1),
                instrument_id=uuid4(),
                eligible=True,
                reason_codes=(UniverseReason.PRICE_TOO_LOW,),
                freeze_at=datetime(2024, 6, 28, 20, 30, tzinfo=UTC),
                source_manifest_hash="a" * 64,
                calculation_version="1",
                frozen_values_hash="b" * 64,
            )

    def test_daily_bar_cannot_be_available_before_observed(self) -> None:
        with self.assertRaises(DataContractError):
            DailyBar(
                instrument_id=uuid4(),
                session_date=date(2024, 11, 29),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=1000,
                observed_at=datetime(2024, 11, 29, 21, 0, tzinfo=UTC),
                available_at=datetime(2024, 11, 29, 20, 59, tzinfo=UTC),
                snapshot_id="snapshot",
            )


if __name__ == "__main__":
    unittest.main()

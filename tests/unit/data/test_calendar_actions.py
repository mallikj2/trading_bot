from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from trading_bot.data.calendars import ExchangeCalendar  # noqa: E402
from trading_bot.data.contracts import CorporateAction, CorporateActionType, ExchangeSession  # noqa: E402
from trading_bot.data.corporate_actions import adjusted_close_as_of, split_adjustment_factor  # noqa: E402
from trading_bot.data.errors import CalendarError  # noqa: E402

UTC = timezone.utc


def session(day: date, open_hour: int, close_hour: int, *, early: bool = False) -> ExchangeSession:
    return ExchangeSession(
        calendar_id="XNYS",
        calendar_version="fixture-v1",
        session_date=day,
        open_at=datetime(day.year, day.month, day.day, open_hour, 30, tzinfo=UTC),
        close_at=datetime(day.year, day.month, day.day, close_hour, 0, tzinfo=UTC),
        early_close=early,
    )


class CalendarAndCorporateActionTests(unittest.TestCase):
    def calendar(self) -> ExchangeCalendar:
        return ExchangeCalendar(
            [
                session(date(2024, 11, 27), 14, 21),
                session(date(2024, 11, 29), 14, 18, early=True),
                session(date(2024, 12, 2), 14, 21),
                session(date(2024, 12, 31), 14, 21),
                session(date(2025, 1, 2), 14, 21),
            ]
        )

    def test_early_close_decision_is_relative(self) -> None:
        calendar = self.calendar()
        self.assertEqual(
            calendar.decision_at(date(2024, 11, 29)),
            datetime(2024, 11, 29, 18, 30, tzinfo=UTC),
        )

    def test_next_session_skips_non_sessions(self) -> None:
        self.assertEqual(self.calendar().next_session(date(2024, 11, 29)).session_date, date(2024, 12, 2))

    def test_universe_freeze_uses_prior_month_final_session(self) -> None:
        self.assertEqual(
            self.calendar().universe_freeze_at(date(2025, 1, 1)),
            datetime(2024, 12, 31, 21, 30, tzinfo=UTC),
        )

    def test_unknown_session_fails(self) -> None:
        with self.assertRaises(CalendarError):
            self.calendar().session(date(2024, 11, 28))

    def test_future_split_does_not_adjust_earlier_decision(self) -> None:
        instrument_id = uuid4()
        action = CorporateAction(
            action_id="split-1",
            instrument_id=instrument_id,
            action_type=CorporateActionType.SPLIT,
            effective_at=datetime(2024, 7, 1, 13, 30, tzinfo=UTC),
            available_at=datetime(2024, 6, 1, tzinfo=UTC),
            source_snapshot_id="s1",
            split_new_shares=Decimal("2"),
            split_old_shares=Decimal("1"),
        )
        factor = split_adjustment_factor(
            instrument_id=instrument_id,
            price_observed_at=datetime(2024, 5, 1, 20, 0, tzinfo=UTC),
            decision_at=datetime(2024, 6, 15, 20, 30, tzinfo=UTC),
            actions=[action],
        )
        self.assertEqual(factor, Decimal("1"))

    def test_effective_known_split_adjusts_prior_price(self) -> None:
        instrument_id = uuid4()
        action = CorporateAction(
            action_id="split-1",
            instrument_id=instrument_id,
            action_type=CorporateActionType.SPLIT,
            effective_at=datetime(2024, 7, 1, 13, 30, tzinfo=UTC),
            available_at=datetime(2024, 6, 1, tzinfo=UTC),
            source_snapshot_id="s1",
            split_new_shares=Decimal("2"),
            split_old_shares=Decimal("1"),
        )
        adjusted = adjusted_close_as_of(
            Decimal("100"),
            instrument_id=instrument_id,
            price_observed_at=datetime(2024, 5, 1, 20, 0, tzinfo=UTC),
            decision_at=datetime(2024, 7, 2, 20, 30, tzinfo=UTC),
            actions=[action],
        )
        self.assertEqual(adjusted, Decimal("50.0"))

    def test_action_unavailable_by_decision_is_not_applied(self) -> None:
        instrument_id = uuid4()
        action = CorporateAction(
            action_id="late-correction",
            instrument_id=instrument_id,
            action_type=CorporateActionType.REVERSE_SPLIT,
            effective_at=datetime(2024, 6, 1, tzinfo=UTC),
            available_at=datetime(2024, 8, 1, tzinfo=UTC),
            source_snapshot_id="s1",
            split_new_shares=Decimal("1"),
            split_old_shares=Decimal("10"),
        )
        factor = split_adjustment_factor(
            instrument_id=instrument_id,
            price_observed_at=datetime(2024, 5, 1, tzinfo=UTC),
            decision_at=datetime(2024, 7, 1, tzinfo=UTC),
            actions=[action],
        )
        self.assertEqual(factor, Decimal("1"))

    def test_latest_known_action_revision_is_used(self) -> None:
        instrument_id = uuid4()
        original = CorporateAction(
            action_id="split-corrected",
            instrument_id=instrument_id,
            action_type=CorporateActionType.SPLIT,
            effective_at=datetime(2024, 7, 1, tzinfo=UTC),
            available_at=datetime(2024, 6, 1, tzinfo=UTC),
            source_snapshot_id="s1",
            revision=0,
            split_new_shares=Decimal("2"),
            split_old_shares=Decimal("1"),
        )
        correction = CorporateAction(
            action_id="split-corrected",
            instrument_id=instrument_id,
            action_type=CorporateActionType.SPLIT,
            effective_at=datetime(2024, 7, 1, tzinfo=UTC),
            available_at=datetime(2024, 6, 15, tzinfo=UTC),
            source_snapshot_id="s2",
            revision=1,
            split_new_shares=Decimal("3"),
            split_old_shares=Decimal("1"),
        )
        factor = split_adjustment_factor(
            instrument_id=instrument_id,
            price_observed_at=datetime(2024, 5, 1, tzinfo=UTC),
            decision_at=datetime(2024, 7, 2, tzinfo=UTC),
            actions=[original, correction],
        )
        self.assertEqual(factor, Decimal("1") / Decimal("3"))

    def test_conflicting_same_action_revision_fails(self) -> None:
        instrument_id = uuid4()
        common = dict(
            action_id="split-conflict",
            instrument_id=instrument_id,
            action_type=CorporateActionType.SPLIT,
            effective_at=datetime(2024, 7, 1, tzinfo=UTC),
            available_at=datetime(2024, 6, 1, tzinfo=UTC),
            revision=1,
            split_old_shares=Decimal("1"),
        )
        left = CorporateAction(source_snapshot_id="s1", split_new_shares=Decimal("2"), **common)
        right = CorporateAction(source_snapshot_id="s2", split_new_shares=Decimal("3"), **common)
        from trading_bot.data.errors import DataContractError
        with self.assertRaises(DataContractError):
            split_adjustment_factor(
                instrument_id=instrument_id,
                price_observed_at=datetime(2024, 5, 1, tzinfo=UTC),
                decision_at=datetime(2024, 7, 2, tzinfo=UTC),
                actions=[left, right],
            )


if __name__ == "__main__":
    unittest.main()

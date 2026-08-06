from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.data.contracts import (
    CorporateAction,
    CorporateActionStatus,
    CorporateActionType,
    DailyBar,
)
from trading_bot.data.errors import DataContractError, PointInTimeError
from trading_bot.data.total_returns import (
    DEFAULT_REQUIRED_COVERAGE_TYPES,
    ActionValuationMethod,
    ActionValuationPurpose,
    CorporateActionCoverage,
    CorporateActionValuation,
    apply_actions_to_position_as_of,
    build_total_return_as_of,
)

UTC = timezone.utc
INSTRUMENT = UUID("00000000-0000-0000-0000-000000000001")
CHILD = UUID("00000000-0000-0000-0000-000000000002")
SUCCESSOR = UUID("00000000-0000-0000-0000-000000000003")


def ts(day: int, hour: int = 20, minute: int = 0) -> datetime:
    return datetime(2025, 6, day, hour, minute, tzinfo=UTC)


def bar(day: int, close: str, *, revision: int = 0, snapshot: str | None = None) -> DailyBar:
    price = Decimal(close)
    return DailyBar(
        instrument_id=INSTRUMENT,
        session_date=date(2025, 6, day),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1_000_000,
        observed_at=ts(day),
        available_at=ts(day, 20, 30),
        snapshot_id=snapshot or f"bar-{day}-{revision}",
        provider_revision=revision,
    )


def coverage(day: int, *, complete: bool = True, types=DEFAULT_REQUIRED_COVERAGE_TYPES):
    return CorporateActionCoverage(
        instrument_id=INSTRUMENT,
        covered_through=ts(day, 23, 59),
        available_at=ts(day, 20, 31),
        covered_types=frozenset(types),
        source_snapshot_id=f"coverage-{day}",
        complete=complete,
    )


def action(
    action_id: str,
    action_type: CorporateActionType,
    day: int,
    **kwargs,
) -> CorporateAction:
    return CorporateAction(
        action_id=action_id,
        instrument_id=INSTRUMENT,
        action_type=action_type,
        effective_at=ts(day, 13, 30),
        available_at=kwargs.pop("available_at", ts(day, 13, 30)),
        source_snapshot_id=kwargs.pop("source_snapshot_id", f"action-{action_id}"),
        **kwargs,
    )


def valuation(
    action_id: str,
    day: int,
    value: str,
    purpose: ActionValuationPurpose,
    *,
    component=CHILD,
    revision: int = 0,
    available_at: datetime | None = None,
) -> CorporateActionValuation:
    return CorporateActionValuation(
        valuation_id=f"valuation-{action_id}-{revision}",
        action_id=action_id,
        instrument_id=INSTRUMENT,
        purpose=purpose,
        valued_at=ts(day, 20, 0),
        available_at=available_at or ts(day, 20, 30),
        value_per_old_share=Decimal(value),
        currency="USD",
        method=ActionValuationMethod.OBSERVED_CHILD_CLOSE,
        source_snapshot_id=f"valuation-snapshot-{action_id}-{revision}",
        revision=revision,
        component_instrument_id=component,
    )


def build(bars, actions=(), valuations=(), decision_day=3, coverage_day=None):
    day = coverage_day or decision_day
    return build_total_return_as_of(
        instrument_id=INSTRUMENT,
        bars=bars,
        actions=actions,
        valuations=valuations,
        coverage=[coverage(day)],
        decision_at=ts(decision_day, 21, 0),
    )


def assert_decimal_close(actual: Decimal, expected: Decimal, tolerance=Decimal("1e-20")):
    assert abs(actual - expected) <= tolerance


def test_split_is_economically_continuous_and_split_adjusted():
    split = action(
        "split-1",
        CorporateActionType.SPLIT,
        3,
        split_old_shares=Decimal("1"),
        split_new_shares=Decimal("2"),
    )
    result = build([bar(2, "100"), bar(3, "50")], [split])
    assert result.adjusted_prices[0].split_adjusted_close == Decimal("50")
    assert result.adjusted_prices[0].total_return_adjusted_close == Decimal("50")
    assert result.total_returns[-1].gross_return == Decimal("1")
    assert result.total_returns[-1].total_return_index == Decimal("100")


def test_future_split_is_invisible_to_earlier_decision():
    split = action(
        "split-future",
        CorporateActionType.SPLIT,
        4,
        split_old_shares=Decimal("1"),
        split_new_shares=Decimal("2"),
        available_at=ts(4, 13, 30),
    )
    result = build(
        [bar(1, "90"), bar(2, "100")],
        [split],
        decision_day=2,
        coverage_day=2,
    )
    assert result.adjusted_prices[0].split_adjusted_close == Decimal("90")
    assert result.adjusted_prices[1].split_adjusted_close == Decimal("100")
    assert not result.event_factors


def test_cash_dividend_produces_flat_total_return_when_price_drops_by_distribution():
    dividend = action(
        "div-1",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="USD",
    )
    result = build([bar(2, "100"), bar(3, "99")], [dividend])
    assert result.adjusted_prices[0].total_return_adjusted_close == Decimal("99")
    assert result.adjusted_prices[0].split_adjusted_close == Decimal("100")
    assert result.total_returns[-1].gross_return == Decimal("1")
    assert result.total_returns[-1].cash_distribution_per_old_share == Decimal("1")


def test_stock_dividend_uses_share_multiplier():
    stock_dividend = action(
        "stock-div-1",
        CorporateActionType.STOCK_DIVIDEND,
        3,
        stock_ratio=Decimal("0.10"),
    )
    ex_close = Decimal("100") / Decimal("1.10")
    result = build([bar(2, "100"), bar(3, str(ex_close))], [stock_dividend])
    assert_decimal_close(result.total_returns[-1].gross_return, Decimal("1"))
    assert_decimal_close(
        result.adjusted_prices[0].split_adjusted_close,
        Decimal("100") / Decimal("1.10"),
    )


def test_spinoff_requires_and_uses_point_in_time_distribution_valuation():
    spinoff = action(
        "spin-1",
        CorporateActionType.SPINOFF,
        3,
        stock_ratio=Decimal("0.5"),
        child_instrument_id=CHILD,
    )
    value = valuation("spin-1", 3, "20", ActionValuationPurpose.DISTRIBUTION)
    result = build([bar(2, "100"), bar(3, "80")], [spinoff], [value])
    assert result.total_returns[-1].gross_return == Decimal("1")
    assert result.total_returns[-1].noncash_distribution_value_per_old_share == Decimal("20")
    assert result.adjusted_prices[0].total_return_adjusted_close == Decimal("80")


def test_spinoff_without_valuation_fails_closed():
    spinoff = action(
        "spin-missing",
        CorporateActionType.SPINOFF,
        3,
        stock_ratio=Decimal("0.5"),
        child_instrument_id=CHILD,
    )
    with pytest.raises(PointInTimeError, match="lacks DISTRIBUTION valuation"):
        build([bar(2, "100"), bar(3, "80")], [spinoff])


def test_cash_and_stock_merger_creates_terminal_return():
    merger = action(
        "merger-1",
        CorporateActionType.MERGER,
        4,
        cash_amount=Decimal("50"),
        currency="USD",
        stock_ratio=Decimal("0.5"),
        successor_instrument_id=SUCCESSOR,
    )
    stock_value = valuation(
        "merger-1",
        4,
        "60",
        ActionValuationPurpose.TERMINAL_CONSIDERATION,
        component=SUCCESSOR,
    )
    result = build(
        [bar(2, "100"), bar(3, "105")],
        [merger],
        [stock_value],
        decision_day=4,
        coverage_day=4,
    )
    terminal = result.total_returns[-1]
    assert terminal.terminal
    assert terminal.raw_close is None
    assert terminal.gross_return == Decimal("110") / Decimal("105")
    assert terminal.action_ids == ("merger-1",)


def test_explicit_zero_recovery_delisting_is_supported():
    delisting = action("delist-1", CorporateActionType.DELISTING, 4)
    zero = CorporateActionValuation(
        valuation_id="zero-recovery",
        action_id="delist-1",
        instrument_id=INSTRUMENT,
        purpose=ActionValuationPurpose.TERMINAL_CONSIDERATION,
        valued_at=ts(4, 13, 30),
        available_at=ts(4, 13, 31),
        value_per_old_share=Decimal("0"),
        currency="USD",
        method=ActionValuationMethod.ZERO_RECOVERY,
        source_snapshot_id="zero-recovery-source",
    )
    result = build(
        [bar(2, "100"), bar(3, "70")],
        [delisting],
        [zero],
        decision_day=4,
        coverage_day=4,
    )
    assert result.total_returns[-1].gross_return == Decimal("0")
    assert result.total_returns[-1].net_return == Decimal("-1")


def test_later_cancellation_does_not_rewrite_earlier_decision_but_is_visible_later():
    original = action(
        "div-revised",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="USD",
        revision=0,
    )
    cancelled = action(
        "div-revised",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="USD",
        status=CorporateActionStatus.CANCELLED,
        revision=1,
        available_at=ts(4, 12, 0),
        source_snapshot_id="cancel-snapshot",
    )
    earlier = build([bar(2, "100"), bar(3, "99")], [original, cancelled], decision_day=3)
    assert earlier.total_returns[-1].gross_return == Decimal("1")
    later = build(
        [bar(2, "100"), bar(3, "99")],
        [original, cancelled],
        decision_day=4,
        coverage_day=4,
    )
    assert later.total_returns[-1].gross_return == Decimal("0.99")
    assert not later.event_factors


def test_incomplete_coverage_blocks_build():
    with pytest.raises(PointInTimeError, match="not marked complete"):
        build_total_return_as_of(
            instrument_id=INSTRUMENT,
            bars=[bar(2, "100"), bar(3, "101")],
            actions=[],
            valuations=[],
            coverage=[coverage(3, complete=False)],
            decision_at=ts(3, 21),
        )


def test_coverage_missing_material_type_blocks_build():
    with pytest.raises(PointInTimeError, match="lacks required types"):
        build_total_return_as_of(
            instrument_id=INSTRUMENT,
            bars=[bar(2, "100"), bar(3, "101")],
            actions=[],
            valuations=[],
            coverage=[coverage(3, types={CorporateActionType.SPLIT})],
            decision_at=ts(3, 21),
        )


def test_unsupported_tender_offer_blocks_build():
    tender = action("tender-1", CorporateActionType.TENDER_OFFER, 3)
    with pytest.raises(PointInTimeError, match="unsupported material"):
        build([bar(2, "100"), bar(3, "102")], [tender])


def test_continuing_action_without_ex_date_bar_blocks_build():
    dividend = action(
        "div-gap",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="USD",
    )
    with pytest.raises(PointInTimeError, match="lacks an ex-date daily bar"):
        build(
            [bar(2, "100"), bar(4, "101")],
            [dividend],
            decision_day=4,
            coverage_day=4,
        )


def test_currency_mismatch_blocks_action_math():
    dividend = action(
        "div-eur",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="EUR",
    )
    with pytest.raises(DataContractError, match="currency mismatch"):
        build([bar(2, "100"), bar(3, "99")], [dividend])


def test_short_dividend_liability_and_split_quantity_are_signed():
    dividend = action(
        "div-short",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("2"),
        currency="USD",
    )
    split = action(
        "split-short",
        CorporateActionType.SPLIT,
        3,
        split_old_shares=Decimal("1"),
        split_new_shares=Decimal("2"),
    )
    effect = apply_actions_to_position_as_of(
        instrument_id=INSTRUMENT,
        quantity=Decimal("-10"),
        effective_at=ts(3, 13, 30),
        actions=[dividend, split],
        valuations=[],
        decision_at=ts(3, 21),
    )
    assert effect.cash_flow == Decimal("-20")
    assert effect.resulting_parent_quantity == Decimal("-20")
    assert not effect.terminal


def test_spinoff_position_distribution_preserves_short_sign():
    spinoff = action(
        "spin-position",
        CorporateActionType.SPINOFF,
        3,
        stock_ratio=Decimal("0.25"),
        child_instrument_id=CHILD,
    )
    value = valuation("spin-position", 3, "10", ActionValuationPurpose.DISTRIBUTION)
    effect = apply_actions_to_position_as_of(
        instrument_id=INSTRUMENT,
        quantity=Decimal("-8"),
        effective_at=ts(3, 13, 30),
        actions=[spinoff],
        valuations=[value],
        decision_at=ts(3, 21),
    )
    assert effect.distributed_positions[0].quantity == Decimal("-2")
    assert effect.fair_value_of_noncash_distributions == Decimal("-80")
    assert effect.resulting_parent_quantity == Decimal("-8")


def test_merger_position_converts_to_successor_and_cash():
    merger = action(
        "merger-position",
        CorporateActionType.MERGER,
        3,
        cash_amount=Decimal("5"),
        currency="USD",
        stock_ratio=Decimal("0.4"),
        successor_instrument_id=SUCCESSOR,
    )
    value = valuation(
        "merger-position",
        3,
        "40",
        ActionValuationPurpose.TERMINAL_CONSIDERATION,
        component=SUCCESSOR,
    )
    effect = apply_actions_to_position_as_of(
        instrument_id=INSTRUMENT,
        quantity=Decimal("10"),
        effective_at=ts(3, 13, 30),
        actions=[merger],
        valuations=[value],
        decision_at=ts(3, 21),
    )
    assert effect.terminal
    assert effect.resulting_parent_quantity == Decimal("0")
    assert effect.cash_flow == Decimal("50")
    assert effect.distributed_positions[0].quantity == Decimal("4.0")
    assert effect.fair_value_of_noncash_distributions == Decimal("400")


def test_adjusted_close_return_matches_forward_total_return_ratio():
    dividend = action(
        "div-match",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="USD",
    )
    result = build([bar(1, "95"), bar(2, "100"), bar(3, "98")], [dividend])
    adjusted = result.adjusted_prices
    adjusted_ratio = adjusted[2].total_return_adjusted_close / adjusted[1].total_return_adjusted_close
    assert adjusted_ratio == result.total_returns[2].gross_return


def test_build_hash_is_deterministic_and_changes_with_action_revision():
    dividend = action(
        "div-hash",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="USD",
    )
    first = build([bar(2, "100"), bar(3, "99")], [dividend])
    second = build([bar(2, "100"), bar(3, "99")], [dividend])
    assert first.build_hash == second.build_hash
    revised = action(
        "div-hash",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1.5"),
        currency="USD",
        revision=1,
        available_at=ts(3, 13, 31),
        source_snapshot_id="revised-dividend",
    )
    third = build([bar(2, "100"), bar(3, "99")], [dividend, revised])
    assert third.build_hash != first.build_hash


def test_conflicting_same_revision_action_records_fail_closed():
    first = action(
        "div-conflict",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("1"),
        currency="USD",
        source_snapshot_id="source-a",
    )
    second = action(
        "div-conflict",
        CorporateActionType.CASH_DIVIDEND,
        3,
        cash_amount=Decimal("2"),
        currency="USD",
        source_snapshot_id="source-b",
    )
    with pytest.raises(PointInTimeError, match="conflicting point-in-time records"):
        build([bar(2, "100"), bar(3, "99")], [first, second])


def test_action_before_selected_history_is_ignored_as_already_embodied_in_raw_prices():
    old_split = action(
        "old-split",
        CorporateActionType.SPLIT,
        1,
        split_old_shares=Decimal("1"),
        split_new_shares=Decimal("2"),
    )
    result = build([bar(2, "50"), bar(3, "51")], [old_split])
    assert not result.event_factors
    assert result.total_returns[-1].gross_return == Decimal("1.02")


def test_economic_action_on_first_selected_bar_requires_prior_bar():
    split = action(
        "first-bar-split",
        CorporateActionType.SPLIT,
        2,
        split_old_shares=Decimal("1"),
        split_new_shares=Decimal("2"),
    )
    with pytest.raises(PointInTimeError, match="prior bar is required"):
        build([bar(2, "50"), bar(3, "51")], [split])

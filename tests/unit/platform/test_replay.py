from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.platform.event_journal import JournalRecord, SQLiteEventJournal
from trading_bot.platform.events import DomainEvent
from trading_bot.platform.leads import (
    BorrowState,
    CostState,
    EarningsState,
    FactorObservation,
    LeadDirection,
    LeadLifecycleState,
    LeadProvenance,
    LeadReason,
    LeadReasonCode,
    LeadTrendState,
    LeadUniverseState,
    LeadVolatilityState,
    TradeLead,
)
from trading_bot.platform.replay import (
    ReplayEngine,
    ReplayError,
    TradeLeadProjector,
    trade_lead_snapshot_event,
)

UTC = timezone.utc
NOW = datetime(2026, 8, 8, 20, 30, tzinfo=UTC)


def lead() -> TradeLead:
    return TradeLead.create(
        instrument_id=UUID("00000000-0000-0000-0000-000000000031"),
        decision_symbol="ALFA",
        decision_symbol_available_at=NOW - timedelta(days=365),
        display_symbol="ALFA",
        display_symbol_as_of=NOW,
        strategy_id="CSMOM-LS",
        strategy_version="0.2",
        generated_at=NOW,
        decision_at=NOW,
        valid_until=NOW + timedelta(days=7),
        direction=LeadDirection.LONG,
        score=Decimal("1.31"),
        factors=(FactorObservation("mom12_1", Decimal("1.4"), NOW),),
        trend_state=LeadTrendState.ABOVE_SMA200,
        volatility_state=LeadVolatilityState.WITHIN_LIMIT,
        universe_state=LeadUniverseState.ELIGIBLE,
        earnings_state=EarningsState.CLEAR,
        cost_state=CostState.CLEAR,
        borrow_state=BorrowState.NOT_APPLICABLE,
        provenance=LeadProvenance(
            dataset_manifest_hash="a" * 64,
            universe_manifest_hash="b" * 64,
            feature_manifest_hash="c" * 64,
            max_input_available_at=NOW,
        ),
        initial_state=LeadLifecycleState.QUALIFIED,
        estimated_spread_bps="9",
        estimated_cost_bps="13",
    )


def journal_with_lead() -> tuple[SQLiteEventJournal, TradeLead, TradeLead]:
    initial = lead()
    planned = initial.with_allocation(proposed_weight="0.17", proposed_shares=3).transition(
        to_state=LeadLifecycleState.PLANNED,
        changed_at=NOW + timedelta(minutes=1),
    )
    first = trade_lead_snapshot_event(initial)
    second = trade_lead_snapshot_event(planned, causation_id=first.event_id)
    journal = SQLiteEventJournal()
    journal.append(first, recorded_at=NOW + timedelta(seconds=1))
    journal.append(second, recorded_at=NOW + timedelta(minutes=1, seconds=1))
    return journal, initial, planned


def test_trade_lead_replay_reconstructs_latest_state() -> None:
    journal, _, planned = journal_with_lead()
    result = ReplayEngine(TradeLeadProjector()).replay_journal(journal)
    replayed = result.state.book.get(planned.lead_id)
    assert replayed is not None
    assert replayed.content_hash == planned.content_hash
    assert result.event_count == 2


def test_replay_is_deterministic_across_fresh_runs() -> None:
    journal, _, _ = journal_with_lead()
    first = ReplayEngine(TradeLeadProjector()).replay_journal(journal)
    second = ReplayEngine(TradeLeadProjector()).replay_journal(journal)
    assert first.state_hash == second.state_hash
    assert first.snapshot == second.snapshot


def test_replay_through_sequence_reconstructs_prior_state() -> None:
    journal, initial, _ = journal_with_lead()
    result = ReplayEngine(TradeLeadProjector()).replay_journal(journal, through_sequence=1)
    replayed = result.state.book.get(initial.lead_id)
    assert replayed is not None
    assert replayed.content_hash == initial.content_hash
    assert result.event_count == 1


def test_replay_rejects_out_of_order_records() -> None:
    journal, _, _ = journal_with_lead()
    records = journal.records()
    with pytest.raises(ReplayError, match="increasing"):
        ReplayEngine(TradeLeadProjector()).replay_records(reversed(records))


def test_replay_rejects_divergent_lead_history() -> None:
    initial = lead()
    planned = initial.with_allocation(proposed_weight="0.17", proposed_shares=3).transition(
        to_state=LeadLifecycleState.PLANNED,
        changed_at=NOW + timedelta(minutes=1),
    )
    rejected = initial.transition(
        to_state=LeadLifecycleState.RISK_REJECTED,
        changed_at=NOW + timedelta(minutes=1),
        reasons=(
            LeadReason(
                code=LeadReasonCode.RISK_LIMIT,
                detail="Synthetic risk rejection for divergent-history replay test.",
                available_at=NOW + timedelta(seconds=30),
            ),
        ),
    )
    first = trade_lead_snapshot_event(initial)
    planned_event = trade_lead_snapshot_event(planned, causation_id=first.event_id)
    rejected_event = trade_lead_snapshot_event(rejected, causation_id=first.event_id)
    journal = SQLiteEventJournal()
    journal.append(first, recorded_at=NOW + timedelta(seconds=1))
    journal.append(planned_event, recorded_at=NOW + timedelta(minutes=1, seconds=1))
    journal.append(rejected_event, recorded_at=NOW + timedelta(minutes=1, seconds=2))
    with pytest.raises(ReplayError, match="conflicting"):
        ReplayEngine(TradeLeadProjector()).replay_journal(journal)


def test_unrelated_events_are_ignored_by_trade_lead_projector() -> None:
    journal, _, planned = journal_with_lead()
    generic = DomainEvent.create(
        event_type="SYSTEM.HEARTBEAT",
        aggregate_type="SYSTEM",
        aggregate_id="research-console",
        occurred_at=NOW + timedelta(minutes=2),
        correlation_id="system",
        producer="tests",
        payload={"status": "OK"},
    )
    journal.append(generic, recorded_at=NOW + timedelta(minutes=2, seconds=1))
    result = ReplayEngine(TradeLeadProjector()).replay_journal(journal)
    assert result.state.book.get(planned.lead_id).content_hash == planned.content_hash
    assert result.event_count == 3


def test_trade_lead_event_id_changes_when_lead_snapshot_changes() -> None:
    initial = lead()
    planned = initial.with_allocation(proposed_weight="0.17", proposed_shares=3).transition(
        to_state=LeadLifecycleState.PLANNED,
        changed_at=NOW + timedelta(minutes=1),
    )
    assert trade_lead_snapshot_event(initial).event_id != trade_lead_snapshot_event(planned).event_id

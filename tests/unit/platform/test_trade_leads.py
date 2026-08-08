from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.platform.leads import (
    BorrowState,
    CostState,
    EarningsState,
    FactorObservation,
    LeadConflictError,
    LeadContractError,
    LeadDirection,
    LeadLifecycleState,
    LeadProvenance,
    LeadReason,
    LeadReasonCode,
    LeadTrendState,
    LeadUniverseState,
    LeadVolatilityState,
    TradeLead,
    TradeLeadBook,
    derive_watchlist_entry,
)

UTC = timezone.utc
DECISION = datetime(2026, 8, 7, 20, 30, tzinfo=UTC)
GENERATED = DECISION + timedelta(minutes=1)
VALID_UNTIL = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)
INSTRUMENT = UUID("11111111-2222-3333-4444-555555555555")
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64


def provenance(*, max_available_at: datetime = DECISION - timedelta(seconds=1)) -> LeadProvenance:
    return LeadProvenance(
        dataset_manifest_hash=H1,
        universe_manifest_hash=H2,
        feature_manifest_hash=H3,
        max_input_available_at=max_available_at,
        source_event_ids=("evt-b", "evt-a"),
    )


def factors(*, available_at: datetime = DECISION - timedelta(seconds=1)) -> tuple[FactorObservation, ...]:
    return (
        FactorObservation("vol20", Decimal("0.24"), available_at),
        FactorObservation("mom_6_1", Decimal("0.15"), available_at),
        FactorObservation("mom_12_1", Decimal("0.32"), available_at),
    )


def reason(code: LeadReasonCode, *, at: datetime = DECISION, detail: str | None = None) -> LeadReason:
    return LeadReason(code, detail or code.value.replace("_", " ").title(), at, True)


def make_lead(
    *,
    direction: LeadDirection = LeadDirection.LONG,
    initial_state: LeadLifecycleState = LeadLifecycleState.QUALIFIED,
    reasons: tuple[LeadReason, ...] = (),
    earnings_state: EarningsState = EarningsState.CLEAR,
    cost_state: CostState = CostState.CLEAR,
    borrow_state: BorrowState | None = None,
    universe_state: LeadUniverseState = LeadUniverseState.ELIGIBLE,
    score: Decimal = Decimal("1.25"),
    prov: LeadProvenance | None = None,
    lead_factors: tuple[FactorObservation, ...] | None = None,
) -> TradeLead:
    if borrow_state is None:
        borrow_state = (
            BorrowState.NOT_APPLICABLE if direction == LeadDirection.LONG else BorrowState.AVAILABLE
        )
    return TradeLead.create(
        instrument_id=INSTRUMENT,
        decision_symbol="TEST",
        decision_symbol_available_at=DECISION - timedelta(days=30),
        display_symbol="TEST",
        display_symbol_as_of=DECISION,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        generated_at=GENERATED,
        decision_at=DECISION,
        valid_until=VALID_UNTIL,
        direction=direction,
        score=score,
        factors=factors() if lead_factors is None else lead_factors,
        trend_state=(
            LeadTrendState.ABOVE_SMA200
            if direction == LeadDirection.LONG
            else LeadTrendState.BELOW_SMA200
        ),
        volatility_state=LeadVolatilityState.WITHIN_LIMIT,
        universe_state=universe_state,
        earnings_state=earnings_state,
        cost_state=cost_state,
        borrow_state=borrow_state,
        provenance=provenance() if prov is None else prov,
        initial_state=initial_state,
        reasons=reasons,
        estimated_spread_bps=Decimal("12.5"),
        estimated_cost_bps=Decimal("18.0"),
    )


def test_create_is_deterministic_and_orders_factors_and_source_events() -> None:
    a = make_lead()
    b = make_lead()
    assert a.lead_id == b.lead_id
    assert a.content_hash == b.content_hash
    assert [factor.name for factor in a.factors] == ["mom_12_1", "mom_6_1", "vol20"]
    assert a.provenance.source_event_ids == ("evt-a", "evt-b")
    assert a.transition_history[0].to_state == LeadLifecycleState.DISCOVERED
    assert a.transition_history[-1].to_state == LeadLifecycleState.QUALIFIED


def test_long_requires_not_applicable_borrow_state() -> None:
    with pytest.raises(LeadContractError, match="LONG leads"):
        make_lead(borrow_state=BorrowState.AVAILABLE)


def test_short_qualified_requires_available_borrow() -> None:
    with pytest.raises(LeadContractError, match="requires borrow AVAILABLE"):
        make_lead(direction=LeadDirection.SHORT, borrow_state=BorrowState.UNKNOWN)


def test_qualified_requires_clear_universe_event_and_cost_context() -> None:
    with pytest.raises(LeadContractError, match="universe ELIGIBLE"):
        make_lead(universe_state=LeadUniverseState.INELIGIBLE)
    with pytest.raises(LeadContractError, match="earnings CLEAR"):
        make_lead(earnings_state=EarningsState.BLOCKED)
    with pytest.raises(LeadContractError, match="cost CLEAR"):
        make_lead(cost_state=CostState.UNCALIBRATED)


def test_future_factor_is_rejected() -> None:
    bad = factors(available_at=DECISION + timedelta(seconds=1))
    with pytest.raises(LeadContractError, match="future information"):
        make_lead(lead_factors=bad)


def test_future_provenance_is_rejected() -> None:
    with pytest.raises(LeadContractError, match="provenance"):
        make_lead(prov=provenance(max_available_at=DECISION + timedelta(microseconds=1)))


def test_future_decision_symbol_is_rejected() -> None:
    good = make_lead()
    with pytest.raises(LeadContractError, match="decision symbol"):
        replace(good, decision_symbol_available_at=DECISION + timedelta(seconds=1))


def test_watchlist_requires_explicit_reason_and_derives_action() -> None:
    lead = make_lead(
        initial_state=LeadLifecycleState.WATCHLIST,
        reasons=(reason(LeadReasonCode.SCORE_THRESHOLD_NOT_MET),),
    )
    entry = derive_watchlist_entry(lead)
    assert entry.state == LeadLifecycleState.WATCHLIST
    assert entry.blocking_reasons[0].code == LeadReasonCode.SCORE_THRESHOLD_NOT_MET
    assert "future decision cycle" in entry.qualification_actions[0]


def test_blocked_state_requires_matching_reason_category() -> None:
    with pytest.raises(LeadContractError, match="EVENT_BLOCKED requires"):
        make_lead(
            initial_state=LeadLifecycleState.EVENT_BLOCKED,
            reasons=(reason(LeadReasonCode.SPREAD_TOO_WIDE),),
            earnings_state=EarningsState.BLOCKED,
        )


def test_blocked_decision_cannot_retroactively_requalify() -> None:
    lead = make_lead(
        initial_state=LeadLifecycleState.EVENT_BLOCKED,
        reasons=(reason(LeadReasonCode.EARNINGS_WINDOW),),
        earnings_state=EarningsState.BLOCKED,
    )
    with pytest.raises(LeadContractError, match="invalid lifecycle transition"):
        lead.transition(LeadLifecycleState.QUALIFIED, changed_at=GENERATED + timedelta(minutes=1))


def test_qualified_to_risk_rejected_then_expires() -> None:
    lead = make_lead()
    rejected = lead.transition(
        LeadLifecycleState.RISK_REJECTED,
        changed_at=GENERATED + timedelta(minutes=2),
        reasons=(reason(LeadReasonCode.RISK_LIMIT, at=GENERATED + timedelta(minutes=1)),),
    )
    assert rejected.score == lead.score
    assert rejected.factors == lead.factors
    expired = rejected.transition(
        LeadLifecycleState.EXPIRED,
        changed_at=VALID_UNTIL,
        reasons=(reason(LeadReasonCode.EXPIRED, at=VALID_UNTIL),),
    )
    assert expired.state == LeadLifecycleState.EXPIRED


def test_happy_path_lifecycle_to_closed() -> None:
    lead = make_lead().with_allocation(proposed_weight=Decimal("0.15"), proposed_shares=3)
    planned = lead.transition(LeadLifecycleState.PLANNED, changed_at=GENERATED + timedelta(minutes=1))
    entered = planned.transition(LeadLifecycleState.ENTERED, changed_at=GENERATED + timedelta(minutes=2))
    exit_pending = entered.transition(
        LeadLifecycleState.EXIT_PENDING, changed_at=VALID_UNTIL + timedelta(days=12)
    )
    closed = exit_pending.transition(
        LeadLifecycleState.CLOSED, changed_at=VALID_UNTIL + timedelta(days=12, minutes=30)
    )
    assert closed.state == LeadLifecycleState.CLOSED
    assert closed.proposed_shares == 3
    assert closed.score == Decimal("1.25")


def test_pre_entry_transition_after_valid_until_is_rejected() -> None:
    lead = make_lead()
    with pytest.raises(LeadContractError, match="validity expired"):
        lead.transition(LeadLifecycleState.PLANNED, changed_at=VALID_UNTIL + timedelta(seconds=1))


def test_expire_before_valid_until_is_rejected() -> None:
    lead = make_lead()
    with pytest.raises(LeadContractError, match="cannot expire before"):
        lead.transition(
            LeadLifecycleState.EXPIRED,
            changed_at=VALID_UNTIL - timedelta(seconds=1),
            reasons=(reason(LeadReasonCode.EXPIRED, at=VALID_UNTIL - timedelta(seconds=1)),),
        )


def test_transition_cannot_use_future_reason() -> None:
    lead = make_lead()
    changed = GENERATED + timedelta(minutes=2)
    with pytest.raises(LeadContractError, match="not yet available"):
        lead.transition(
            LeadLifecycleState.COST_BLOCKED,
            changed_at=changed,
            reasons=(reason(LeadReasonCode.SPREAD_TOO_WIDE, at=changed + timedelta(seconds=1)),),
        )


def test_duplicate_transition_delivery_is_idempotent() -> None:
    lead = make_lead()
    changed = GENERATED + timedelta(minutes=2)
    reasons = (reason(LeadReasonCode.RISK_LIMIT, at=changed),)
    rejected = lead.transition(LeadLifecycleState.RISK_REJECTED, changed_at=changed, reasons=reasons)
    duplicate = rejected.transition(LeadLifecycleState.RISK_REJECTED, changed_at=changed, reasons=reasons)
    assert duplicate is rejected


def test_allocation_is_once_only_and_directionally_validated() -> None:
    lead = make_lead()
    allocated = lead.with_allocation(proposed_weight="0.20", proposed_shares=4)
    assert allocated.with_allocation(proposed_weight="0.20", proposed_shares=4) is allocated
    with pytest.raises(LeadConflictError, match="immutable once assigned"):
        allocated.with_allocation(proposed_weight="0.15", proposed_shares=3)
    with pytest.raises(LeadContractError, match="cannot be negative"):
        lead.with_allocation(proposed_weight="-0.10", proposed_shares=2)


def test_short_allocation_must_be_negative() -> None:
    lead = make_lead(direction=LeadDirection.SHORT)
    with pytest.raises(LeadContractError, match="cannot be positive"):
        lead.with_allocation(proposed_weight="0.10", proposed_shares=2)
    allocated = lead.with_allocation(proposed_weight="-0.10", proposed_shares=2)
    assert allocated.proposed_weight == Decimal("-0.10")


def test_serialization_round_trip_is_lossless() -> None:
    lead = make_lead().with_allocation(proposed_weight="0.10", proposed_shares=2)
    raw = lead.to_json()
    rebuilt = TradeLead.from_json(raw)
    assert rebuilt == lead
    assert rebuilt.content_hash == lead.content_hash
    assert rebuilt.to_json() == raw


def test_display_symbol_is_presentation_only_and_keeps_lead_identity() -> None:
    lead = make_lead()
    updated = lead.with_display_symbol(display_symbol="NEW", as_of=DECISION + timedelta(days=30))
    assert updated.lead_id == lead.lead_id
    assert updated.immutable_fingerprint == lead.immutable_fingerprint
    assert updated.decision_symbol == "TEST"
    assert updated.display_symbol == "NEW"


def test_watchlist_cannot_be_derived_from_qualified_lead() -> None:
    with pytest.raises(LeadContractError, match="does not belong on the watchlist"):
        derive_watchlist_entry(make_lead())


def test_book_accepts_duplicate_and_lifecycle_extension() -> None:
    book = TradeLeadBook()
    lead = make_lead()
    assert book.ingest(lead) is lead
    assert book.ingest(make_lead()).content_hash == lead.content_hash
    planned = lead.with_allocation(proposed_weight="0.10", proposed_shares=2).transition(
        LeadLifecycleState.PLANNED, changed_at=GENERATED + timedelta(minutes=1)
    )
    assert book.ingest(planned).state == LeadLifecycleState.PLANNED
    assert book.ingest(lead).state == LeadLifecycleState.PLANNED  # stale snapshot ignored


def test_book_rejects_score_conflict_for_same_lead_id() -> None:
    book = TradeLeadBook()
    lead = make_lead()
    book.ingest(lead)
    conflicting = replace(lead, score=Decimal("1.99"))
    with pytest.raises(LeadConflictError, match="immutable research content"):
        book.ingest(conflicting)


def test_book_rejects_divergent_history() -> None:
    book = TradeLeadBook()
    lead = make_lead()
    risk = lead.transition(
        LeadLifecycleState.RISK_REJECTED,
        changed_at=GENERATED + timedelta(minutes=1),
        reasons=(reason(LeadReasonCode.RISK_LIMIT, at=GENERATED + timedelta(minutes=1)),),
    )
    cost = lead.transition(
        LeadLifecycleState.COST_BLOCKED,
        changed_at=GENERATED + timedelta(minutes=1),
        reasons=(reason(LeadReasonCode.SPREAD_TOO_WIDE, at=GENERATED + timedelta(minutes=1)),),
    )
    book.ingest(risk)
    with pytest.raises(LeadConflictError, match="divergent lifecycle history"):
        book.ingest(cost)


def test_domain_has_no_order_submission_surface() -> None:
    import trading_bot.platform.leads as leads_module

    banned = {"buy", "sell", "short", "submit_order", "cancel_order", "place_order"}
    exported = {name.lower() for name in dir(leads_module) if not name.startswith("_")}
    assert not (banned & exported)


def test_planned_state_requires_concrete_allocation() -> None:
    lead = make_lead()
    with pytest.raises(LeadContractError, match="PLANNED requires a proposed allocation"):
        lead.transition(LeadLifecycleState.PLANNED, changed_at=GENERATED + timedelta(minutes=1))


def test_borrow_blocked_state_is_short_only() -> None:
    with pytest.raises(LeadContractError, match="only valid for SHORT"):
        make_lead(
            initial_state=LeadLifecycleState.BORROW_BLOCKED,
            reasons=(reason(LeadReasonCode.BORROW_UNAVAILABLE),),
            borrow_state=BorrowState.NOT_APPLICABLE,
        )


def test_committed_trade_lead_fixture_cases_are_supported() -> None:
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[2] / "fixtures" / "platform" / "trade_lead_cases.json"
    payload = json.loads(fixture_path.read_text())
    assert payload["schema_version"] == "1.0"
    for case in payload["cases"]:
        direction = LeadDirection(case["direction"])
        state = LeadLifecycleState(case["state"])
        raw_reason = case["reason"]
        case_reasons = () if raw_reason is None else (reason(LeadReasonCode(raw_reason)),)
        borrow = BorrowState.NOT_APPLICABLE if direction == LeadDirection.LONG else BorrowState.AVAILABLE
        if state == LeadLifecycleState.BORROW_BLOCKED:
            borrow = BorrowState.BLOCKED
        lead = make_lead(
            direction=direction,
            initial_state=state,
            reasons=case_reasons,
            borrow_state=borrow,
            score=Decimal(case["score"]),
        )
        assert lead.state == state
        if state == LeadLifecycleState.WATCHLIST:
            entry = derive_watchlist_entry(lead)
            assert case["expected_action_contains"] in entry.qualification_actions[0]

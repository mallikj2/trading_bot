from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

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
    TradeLeadBook,
    derive_watchlist_entry,
)

UTC = timezone.utc


def test_tradelead_watchlist_to_audit_projection_is_deterministic() -> None:
    decision = datetime(2026, 8, 7, 20, 30, tzinfo=UTC)
    generated = decision + timedelta(seconds=10)
    valid_until = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)
    prov = LeadProvenance(
        dataset_manifest_hash="a" * 64,
        universe_manifest_hash="b" * 64,
        feature_manifest_hash="c" * 64,
        max_input_available_at=decision - timedelta(seconds=1),
        source_event_ids=("feature-build-123",),
    )
    score_reason = LeadReason(
        LeadReasonCode.SCORE_THRESHOLD_NOT_MET,
        "Score +0.69 is below the frozen +0.75 long threshold.",
        decision,
    )
    lead = TradeLead.create(
        instrument_id=UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        decision_symbol="WATCH",
        decision_symbol_available_at=decision - timedelta(days=365),
        display_symbol="WATCH",
        display_symbol_as_of=decision,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        generated_at=generated,
        decision_at=decision,
        valid_until=valid_until,
        direction=LeadDirection.LONG,
        score=Decimal("0.69"),
        factors=(
            FactorObservation("mom_12_1", Decimal("0.21"), decision - timedelta(seconds=1)),
            FactorObservation("mom_6_1", Decimal("0.11"), decision - timedelta(seconds=1)),
            FactorObservation("vol20", Decimal("0.29"), decision - timedelta(seconds=1)),
        ),
        trend_state=LeadTrendState.ABOVE_SMA200,
        volatility_state=LeadVolatilityState.WITHIN_LIMIT,
        universe_state=LeadUniverseState.ELIGIBLE,
        earnings_state=EarningsState.CLEAR,
        cost_state=CostState.CLEAR,
        borrow_state=BorrowState.NOT_APPLICABLE,
        provenance=prov,
        initial_state=LeadLifecycleState.WATCHLIST,
        reasons=(score_reason,),
        estimated_spread_bps=Decimal("11.0"),
        estimated_cost_bps=Decimal("16.5"),
    )

    entry = derive_watchlist_entry(lead)
    book = TradeLeadBook()
    stored = book.ingest(lead)
    rehydrated = TradeLead.from_json(stored.to_json())

    assert rehydrated.content_hash == stored.content_hash
    assert entry.lead_content_hash == stored.content_hash
    assert entry.blocking_reasons[0].detail.startswith("Score +0.69")
    assert entry.qualification_actions == (
        "Await a future decision cycle whose frozen score meets the strategy threshold.",
    )
    assert book.ingest(rehydrated).content_hash == stored.content_hash

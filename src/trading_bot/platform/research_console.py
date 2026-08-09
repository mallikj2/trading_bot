"""Read-only research console projection layer for P02-PF02.

This module deliberately contains no broker adapters and no mutation methods.
It projects immutable PF01 TradeLead artifacts and fixture-backed platform status
into JSON-safe read models consumed by the FastAPI/React research console.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Iterable
from uuid import UUID


from trading_bot.platform.experiments import build_pf08_fixture_report
from trading_bot.platform.alerts import build_pf09_fixture_incident_report
from trading_bot.platform.recovery import build_pf10_fixture_recovery_report

from trading_bot.platform.runtime_safety import (
    ProtectionEngine,
    ProtectionObservation,
    ProtectionScope,
    ProtectionStatus,
    RuntimeSafetyState,
    StatusProtectionRule,
    StalenessProtectionRule,
    permissions_for,
)
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


@dataclass(frozen=True, slots=True)
class PortfolioPositionView:
    symbol: str
    side: str
    shares: int
    market_value: Decimal
    unrealized_pnl: Decimal
    sector: str
    holding_sessions: int
    source: str = "SYNTHETIC_FIXTURE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "shares": self.shares,
            "market_value": str(self.market_value),
            "unrealized_pnl": str(self.unrealized_pnl),
            "sector": self.sector,
            "holding_sessions": self.holding_sessions,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class AuditRecordView:
    occurred_at: datetime
    category: str
    entity_id: str
    summary: str
    provenance_hash: str

    def to_dict(self) -> dict[str, str]:
        return {
            "occurred_at": self.occurred_at.isoformat(),
            "category": self.category,
            "entity_id": self.entity_id,
            "summary": self.summary,
            "provenance_hash": self.provenance_hash,
        }


@dataclass(frozen=True, slots=True)
class ResearchConsoleSnapshot:
    generated_at: datetime
    leads: tuple[TradeLead, ...]
    positions: tuple[PortfolioPositionView, ...]
    audit_records: tuple[AuditRecordView, ...]
    data_gates: tuple[dict[str, Any], ...]
    data_health: tuple[dict[str, Any], ...]
    runtime_state: str = "ACTIVE"
    runtime_protections: tuple[dict[str, Any], ...] = ()
    runtime_recovery_required: bool = False
    runtime_permissions: dict[str, bool] = field(default_factory=lambda: permissions_for(RuntimeSafetyState.ACTIVE).to_dict())
    strategy_validation: dict[str, Any] = field(default_factory=dict)
    experiment_reporting: dict[str, Any] = field(default_factory=dict)
    incident_reporting: dict[str, Any] = field(default_factory=dict)
    recovery_reporting: dict[str, Any] = field(default_factory=dict)
    environment: str = "PHASE_02_FIXTURE"

    def _lead_view(self, lead: TradeLead) -> dict[str, Any]:
        reasons = [reason.to_dict() for reason in lead.active_reasons]
        return {
            "lead_id": lead.lead_id,
            "instrument_id": str(lead.instrument_id),
            "symbol": lead.display_symbol,
            "decision_symbol": lead.decision_symbol,
            "direction": lead.direction.value,
            "score": str(lead.score),
            "state": lead.state.value,
            "trend_state": lead.trend_state.value,
            "volatility_state": lead.volatility_state.value,
            "earnings_state": lead.earnings_state.value,
            "cost_state": lead.cost_state.value,
            "borrow_state": lead.borrow_state.value,
            "estimated_spread_bps": None if lead.estimated_spread_bps is None else str(lead.estimated_spread_bps),
            "estimated_cost_bps": None if lead.estimated_cost_bps is None else str(lead.estimated_cost_bps),
            "proposed_weight": None if lead.proposed_weight is None else str(lead.proposed_weight),
            "proposed_shares": lead.proposed_shares,
            "decision_at": lead.decision_at.isoformat(),
            "valid_until": lead.valid_until.isoformat(),
            "strategy_id": lead.strategy_id,
            "strategy_version": lead.strategy_version,
            "reasons": reasons,
            "factors": [factor.to_dict() for factor in lead.factors],
            "provenance": lead.provenance.to_dict(),
            "immutable_hash": lead.immutable_fingerprint,
            "content_hash": lead.content_hash,
        }

    def overview(self) -> dict[str, Any]:
        lead_counts: dict[str, int] = {}
        for lead in self.leads:
            lead_counts[lead.state.value] = lead_counts.get(lead.state.value, 0) + 1
        gross = sum(abs(position.market_value) for position in self.positions)
        net = sum(
            position.market_value if position.side == "LONG" else -position.market_value
            for position in self.positions
        )
        blocked_gates = sum(1 for gate in self.data_gates if gate["status"] != "PASS")
        unhealthy = sum(1 for row in self.data_health if row["status"] not in {"PASS", "OK"})
        return {
            "generated_at": self.generated_at.isoformat(),
            "environment": self.environment,
            "runtime_state": self.runtime_state,
            "phase": "PHASE_02",
            "phase03_authorized": False,
            "procurement_authorized": False,
            "lead_counts": lead_counts,
            "portfolio": {
                "position_count": len(self.positions),
                "gross_market_value": str(gross),
                "net_market_value": str(net),
            },
            "gate_summary": {
                "total": len(self.data_gates),
                "blocked_or_nonpass": blocked_gates,
            },
            "data_health_summary": {
                "total": len(self.data_health),
                "nonpass": unhealthy,
            },
            "fixture_notice": "Synthetic/read-only Phase 02 console. No live orders or broker state.",
        }

    def trade_leads(self) -> list[dict[str, Any]]:
        visible = {
            LeadLifecycleState.QUALIFIED,
            LeadLifecycleState.PLANNED,
            LeadLifecycleState.RISK_REJECTED,
            LeadLifecycleState.EVENT_BLOCKED,
            LeadLifecycleState.COST_BLOCKED,
            LeadLifecycleState.BORROW_BLOCKED,
            LeadLifecycleState.PORTFOLIO_REJECTED,
        }
        return [self._lead_view(lead) for lead in sorted(self.leads, key=lambda item: (-abs(item.score), item.lead_id)) if lead.state in visible]

    def watchlist(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for lead in self.leads:
            try:
                entry = derive_watchlist_entry(lead)
            except Exception:
                continue
            entries.append(entry.to_dict())
        return sorted(entries, key=lambda item: (item["direction"], item["symbol"], item["lead_id"]))

    def portfolio(self) -> dict[str, Any]:
        return {
            "mode": "SYNTHETIC_RESEARCH_PLACEHOLDER",
            "positions": [position.to_dict() for position in self.positions],
            "warning": "PF02 portfolio values are fixtures only; no broker/account connection exists.",
        }

    def risk(self) -> dict[str, Any]:
        longs = sum(1 for position in self.positions if position.side == "LONG")
        shorts = sum(1 for position in self.positions if position.side == "SHORT")
        runtime_blocks_new_risk = not self.runtime_permissions.get("simulate_increase_exposure", False)
        return {
            "runtime_state": self.runtime_state,
            "new_risk_allowed": False,
            "reason": "PHASE_02_GOVERNANCE_BLOCKS_ORDER_AUTHORITY",
            "runtime_blocks_new_risk": runtime_blocks_new_risk,
            "runtime_recovery_required": self.runtime_recovery_required,
            "runtime_permissions": dict(self.runtime_permissions),
            "protections": [dict(row) for row in self.runtime_protections],
            "position_counts": {"long": longs, "short": shorts},
            "hard_boundaries": [
                "NO_LIVE_ORDER_SUBMISSION",
                "NO_DEPLOYED_PAPER_TRADING",
                "NO_FRONTEND_STRATEGY_LOGIC",
                "NO_FRONTEND_SECRET_STORAGE",
                "PROTECTIONS_CANNOT_CHANGE_FROZEN_ALPHA_RULES",
            ],
        }

    def gates(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.data_gates]

    def health(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.data_health]

    def audit(self) -> list[dict[str, str]]:
        return [record.to_dict() for record in sorted(self.audit_records, key=lambda item: item.occurred_at, reverse=True)]

    def validation(self) -> dict[str, Any]:
        return dict(self.strategy_validation)

    def experiments(self) -> dict[str, Any]:
        return dict(self.experiment_reporting)

    def incidents(self) -> dict[str, Any]:
        return dict(self.incident_reporting)

    def recovery(self) -> dict[str, Any]:
        return dict(self.recovery_reporting)


class ReadOnlyResearchConsole:
    """Read-only query service; intentionally has no mutation surface."""

    def __init__(self, snapshot: ResearchConsoleSnapshot) -> None:
        self._snapshot = snapshot

    def overview(self) -> dict[str, Any]:
        return self._snapshot.overview()

    def trade_leads(self) -> list[dict[str, Any]]:
        return self._snapshot.trade_leads()

    def watchlist(self) -> list[dict[str, Any]]:
        return self._snapshot.watchlist()

    def portfolio(self) -> dict[str, Any]:
        return self._snapshot.portfolio()

    def risk(self) -> dict[str, Any]:
        return self._snapshot.risk()

    def gates(self) -> list[dict[str, Any]]:
        return self._snapshot.gates()

    def data_health(self) -> list[dict[str, Any]]:
        return self._snapshot.health()

    def audit(self) -> list[dict[str, str]]:
        return self._snapshot.audit()

    def strategy_validation(self) -> dict[str, Any]:
        return self._snapshot.validation()

    def experiments(self) -> dict[str, Any]:
        return self._snapshot.experiments()

    def incidents(self) -> dict[str, Any]:
        return self._snapshot.incidents()

    def recovery(self) -> dict[str, Any]:
        return self._snapshot.recovery()


def _hash(char: str) -> str:
    return char * 64


def _fixture_lead(
    *,
    instrument_id: str,
    symbol: str,
    direction: LeadDirection,
    score: str,
    state: LeadLifecycleState,
    reason: LeadReason | None,
    decision_at: datetime,
    spread_bps: str,
    cost_bps: str,
) -> TradeLead:
    reasons: tuple[LeadReason, ...] = () if reason is None else (reason,)
    borrow_state = BorrowState.NOT_APPLICABLE if direction == LeadDirection.LONG else BorrowState.AVAILABLE
    earnings_state = EarningsState.CLEAR
    cost_state = CostState.CLEAR
    if state == LeadLifecycleState.EVENT_BLOCKED:
        earnings_state = EarningsState.BLOCKED
    if state == LeadLifecycleState.COST_BLOCKED:
        cost_state = CostState.BLOCKED
    if state == LeadLifecycleState.BORROW_BLOCKED:
        borrow_state = BorrowState.BLOCKED
    lead = TradeLead.create(
        instrument_id=UUID(instrument_id),
        decision_symbol=symbol,
        decision_symbol_available_at=decision_at - timedelta(days=365),
        display_symbol=symbol,
        display_symbol_as_of=decision_at,
        strategy_id="CSMOM-LS",
        strategy_version="0.2",
        generated_at=decision_at,
        decision_at=decision_at,
        valid_until=decision_at + timedelta(days=7),
        direction=direction,
        score=score,
        factors=(
            FactorObservation("MOM12_1_Z", Decimal(score), decision_at),
            FactorObservation("MOM6_1_Z", Decimal(score) * Decimal("0.8"), decision_at),
        ),
        trend_state=LeadTrendState.ABOVE_SMA200 if direction == LeadDirection.LONG else LeadTrendState.BELOW_SMA200,
        volatility_state=LeadVolatilityState.WITHIN_LIMIT,
        universe_state=LeadUniverseState.ELIGIBLE,
        earnings_state=earnings_state,
        cost_state=cost_state,
        borrow_state=borrow_state,
        provenance=LeadProvenance(
            dataset_manifest_hash=_hash("a"),
            universe_manifest_hash=_hash("b"),
            feature_manifest_hash=_hash("c"),
            max_input_available_at=decision_at,
            source_event_ids=(f"fixture:{symbol}",),
        ),
        initial_state=state,
        reasons=reasons,
        estimated_spread_bps=spread_bps,
        estimated_cost_bps=cost_bps,
    )
    return lead


def build_fixture_console(*, as_of: datetime | None = None) -> ReadOnlyResearchConsole:
    """Build deterministic fixture-backed console data for PF02 tests and local UI."""
    now = as_of or datetime(2026, 8, 8, 20, 30, tzinfo=UTC)
    reason_score = LeadReason(
        code=LeadReasonCode.SCORE_THRESHOLD_NOT_MET,
        detail="Frozen score 0.69 is below the 0.75 long qualification threshold.",
        available_at=now,
    )
    reason_borrow = LeadReason(
        code=LeadReasonCode.BORROW_UNAVAILABLE,
        detail="Approved historical borrow evidence is unavailable for this short candidate.",
        available_at=now,
    )
    reason_cost = LeadReason(
        code=LeadReasonCode.SPREAD_TOO_WIDE,
        detail="Estimated spread 43 bps exceeds the approved 35 bps gate.",
        available_at=now,
    )
    leads = (
        _fixture_lead(
            instrument_id="00000000-0000-0000-0000-000000000001",
            symbol="ALFA",
            direction=LeadDirection.LONG,
            score="1.31",
            state=LeadLifecycleState.QUALIFIED,
            reason=None,
            decision_at=now,
            spread_bps="9",
            cost_bps="13",
        ),
        _fixture_lead(
            instrument_id="00000000-0000-0000-0000-000000000002",
            symbol="BETA",
            direction=LeadDirection.LONG,
            score="0.69",
            state=LeadLifecycleState.WATCHLIST,
            reason=reason_score,
            decision_at=now,
            spread_bps="8",
            cost_bps="12",
        ),
        _fixture_lead(
            instrument_id="00000000-0000-0000-0000-000000000003",
            symbol="GAMM",
            direction=LeadDirection.SHORT,
            score="-1.18",
            state=LeadLifecycleState.BORROW_BLOCKED,
            reason=reason_borrow,
            decision_at=now,
            spread_bps="17",
            cost_bps="24",
        ),
        _fixture_lead(
            instrument_id="00000000-0000-0000-0000-000000000004",
            symbol="DELT",
            direction=LeadDirection.LONG,
            score="1.02",
            state=LeadLifecycleState.COST_BLOCKED,
            reason=reason_cost,
            decision_at=now,
            spread_bps="43",
            cost_bps="52",
        ),
    )
    # Exercise PF01 book idempotency/provenance validation in fixture construction.
    book = TradeLeadBook()
    for lead in leads:
        book.ingest(lead)
    gate_rows = (
        {"gate_id": "P02-PF01", "name": "TradeLead + Watchlist", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF02", "name": "Read-only API + Research Console", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF03", "name": "Event Journal + Replay", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF04", "name": "Runtime Safety + Protections", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF05", "name": "Lookahead + Recursive Validation", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF06", "name": "OMS + SimulatedBroker", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF07", "name": "Deterministic Simulation Runtime", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF08", "name": "Experiment Registry + Reporting + Attribution", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF09", "name": "Alerts + Incident Center", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-PF10", "name": "Recovery + Reconciliation Simulation", "status": "PASS", "category": "PLATFORM"},
        {"gate_id": "P02-G04", "name": "Core provider credentialed trial", "status": "BLOCKED", "category": "DATA"},
        {"gate_id": "P02-G18", "name": "PIT security master + exact execution", "status": "BLOCKED", "category": "DATA"},
    )
    health_rows = (
        {"component": "PF01_LEAD_FIXTURES", "status": "PASS", "freshness": "STATIC", "detail": "Deterministic synthetic fixtures loaded."},
        {"component": "PF05_STRATEGY_VALIDATION", "status": "PASS", "freshness": "STATIC", "detail": "Clean synthetic lookahead and recursive validation fixtures passed; contaminated controls failed as expected."},
        {"component": "PF08_EXPERIMENT_REGISTRY", "status": "PASS", "freshness": "STATIC", "detail": "Immutable synthetic experiment definitions/runs and attribution fixtures verified; not Phase 03 evidence."},
        {"component": "PF09_INCIDENT_CENTER", "status": "PASS", "freshness": "STATIC", "detail": "Deterministic synthetic alert deduplication, escalation, acknowledgement and resolution fixtures verified."},
        {"component": "PF10_RECOVERY_RECONCILIATION", "status": "PASS", "freshness": "STATIC", "detail": "Crash-window, missed-fill and divergence recovery fixtures verified without real broker access."},
        {"component": "COMMERCIAL_MARKET_DATA", "status": "BLOCKED", "freshness": "NOT_CONNECTED", "detail": "Procurement intentionally deferred until P02-PF-GATE."},
        {"component": "BROKER", "status": "BLOCKED", "freshness": "NOT_CONNECTED", "detail": "No broker connectivity is permitted in Phase 02B."},
    )
    audit_records = tuple(
        AuditRecordView(
            occurred_at=lead.generated_at,
            category="TRADE_LEAD",
            entity_id=lead.lead_id,
            summary=f"{lead.display_symbol} {lead.direction.value} lead created in {lead.state.value} state.",
            provenance_hash=lead.content_hash,
        )
        for lead in leads
    )
    positions = (
        PortfolioPositionView("ALFA", "LONG", 3, Decimal("612.00"), Decimal("18.50"), "Technology", 7),
        PortfolioPositionView("OMEG", "SHORT", 2, Decimal("318.00"), Decimal("-4.20"), "Industrials", 4),
    )
    strategy_validation = {
        "mode": "SYNTHETIC_PF05_FIXTURE",
        "strategy_id": "CSMOM-LS-v0.2",
        "status": "PASS",
        "lookahead": {"status": "PASS", "difference_count": 0, "method": "FULL_VS_TRUNCATED_AT_DECISION"},
        "recursive": {"status": "PASS", "difference_count": 0, "warmup_sessions": [300, 320, 360]},
        "contaminated_controls": {
            "future_row_dependency": "FAIL_AS_EXPECTED",
            "history_start_dependency": "FAIL_AS_EXPECTED",
            "future_exit_dependency": "FAIL_AS_EXPECTED",
        },
        "live_acceptance_backtest_validated": False,
        "notice": "PF05 synthetic validation evidence only; Phase 03 remains unauthorized.",
    }
    safety_engine = ProtectionEngine((
        StatusProtectionRule("JOURNAL_INTEGRITY", ProtectionScope.JOURNAL),
        StatusProtectionRule("CONFIG_INTEGRITY", ProtectionScope.CONFIG),
        StalenessProtectionRule(
            "RESEARCH_DATA_FRESHNESS",
            ProtectionScope.DATA,
            reduce_after=timedelta(minutes=5),
            halt_after=timedelta(minutes=15),
        ),
    ))
    safety_observations = (
        ProtectionObservation(
            "JOURNAL_INTEGRITY", ProtectionScope.JOURNAL, ProtectionStatus.HEALTHY,
            now, now, now + timedelta(hours=1), "JOURNAL_VERIFIED",
            "PF03 append-only journal integrity verified for fixture state.", _hash("7"),
        ),
        ProtectionObservation(
            "CONFIG_INTEGRITY", ProtectionScope.CONFIG, ProtectionStatus.HEALTHY,
            now, now, now + timedelta(hours=1), "CONFIG_VERIFIED",
            "Version-controlled Phase 02 configuration is internally consistent.", _hash("8"),
        ),
        ProtectionObservation(
            "RESEARCH_DATA_FRESHNESS", ProtectionScope.DATA, ProtectionStatus.HEALTHY,
            now - timedelta(minutes=1), now - timedelta(minutes=1), now + timedelta(minutes=14),
            "FIXTURE_DATA_FRESH", "Synthetic fixture data is within the PF04 freshness window.", _hash("9"),
        ),
    )
    safety_evaluation = safety_engine.evaluate(safety_observations, evaluated_at=now)
    return ReadOnlyResearchConsole(
        ResearchConsoleSnapshot(
            generated_at=now,
            leads=leads,
            positions=positions,
            audit_records=audit_records,
            data_gates=gate_rows,
            data_health=health_rows,
            runtime_state=safety_evaluation.required_state.value,
            runtime_protections=tuple(decision.to_dict() for decision in safety_evaluation.decisions),
            runtime_recovery_required=False,
            runtime_permissions=permissions_for(safety_evaluation.required_state).to_dict(),
            strategy_validation=strategy_validation,
            experiment_reporting=build_pf08_fixture_report(as_of=now),
            incident_reporting=build_pf09_fixture_incident_report(as_of=now),
            recovery_reporting=build_pf10_fixture_recovery_report(as_of=now),
        )
    )

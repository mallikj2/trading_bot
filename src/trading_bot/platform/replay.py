"""Deterministic replay/projector utilities for the PF03 event journal."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Generic, Iterable, Protocol, TypeVar

from trading_bot.platform.event_journal import JournalRecord, SQLiteEventJournal
from trading_bot.platform.events import DomainEvent, canonical_json
from trading_bot.platform.leads import LeadConflictError, TradeLead, TradeLeadBook


StateT = TypeVar("StateT")


class ReplayError(RuntimeError):
    """Replay cannot produce a deterministic/valid state."""


class Projector(Protocol[StateT]):
    def initial_state(self) -> StateT: ...
    def apply(self, state: StateT, event: DomainEvent) -> StateT: ...
    def snapshot(self, state: StateT) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ReplayResult(Generic[StateT]):
    event_count: int
    first_sequence: int | None
    last_sequence: int | None
    journal_head_hash: str
    state_hash: str
    state: StateT
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_count": self.event_count,
            "first_sequence": self.first_sequence,
            "last_sequence": self.last_sequence,
            "journal_head_hash": self.journal_head_hash,
            "state_hash": self.state_hash,
            "snapshot": self.snapshot,
        }


class ReplayEngine(Generic[StateT]):
    def __init__(self, projector: Projector[StateT]) -> None:
        self.projector = projector

    def replay_records(self, records: Iterable[JournalRecord]) -> ReplayResult[StateT]:
        materialized = tuple(records)
        state = self.projector.initial_state()
        previous_sequence: int | None = None
        for record in materialized:
            if previous_sequence is not None and record.sequence <= previous_sequence:
                raise ReplayError("replay records must be in strictly increasing sequence order")
            state = self.projector.apply(state, record.event)
            previous_sequence = record.sequence
        snapshot = self.projector.snapshot(state)
        state_hash = sha256(canonical_json(snapshot).encode("utf-8")).hexdigest()
        return ReplayResult(
            event_count=len(materialized),
            first_sequence=None if not materialized else materialized[0].sequence,
            last_sequence=None if not materialized else materialized[-1].sequence,
            journal_head_hash=("0" * 64) if not materialized else materialized[-1].chain_hash,
            state_hash=state_hash,
            state=state,
            snapshot=snapshot,
        )

    def replay_journal(
        self,
        journal: SQLiteEventJournal,
        *,
        through_sequence: int | None = None,
    ) -> ReplayResult[StateT]:
        journal.verify_integrity()
        records = journal.records(through_sequence=through_sequence)
        return self.replay_records(records)


TRADE_LEAD_SNAPSHOT_EVENT = "TRADE_LEAD.SNAPSHOT"


def trade_lead_snapshot_event(
    lead: TradeLead,
    *,
    causation_id: str | None = None,
) -> DomainEvent:
    latest_transition_at = lead.transition_history[-1].changed_at
    return DomainEvent.create(
        event_type=TRADE_LEAD_SNAPSHOT_EVENT,
        aggregate_type="TRADE_LEAD",
        aggregate_id=lead.lead_id,
        occurred_at=latest_transition_at,
        correlation_id=lead.lead_id,
        causation_id=causation_id,
        producer="trade_lead_domain",
        schema_version=1,
        payload={"lead": lead.to_dict()},
    )


class TradeLeadReplayState:
    """Replay state wrapper preserving PF01 conflict/idempotency semantics."""

    def __init__(self) -> None:
        self.book = TradeLeadBook()


class TradeLeadProjector(Projector[TradeLeadReplayState]):
    def initial_state(self) -> TradeLeadReplayState:
        return TradeLeadReplayState()

    def apply(self, state: TradeLeadReplayState, event: DomainEvent) -> TradeLeadReplayState:
        if event.event_type != TRADE_LEAD_SNAPSHOT_EVENT:
            return state
        if event.aggregate_type != "TRADE_LEAD":
            raise ReplayError("TRADE_LEAD.SNAPSHOT must use TRADE_LEAD aggregate_type")
        raw_lead = event.payload.get("lead")
        if not isinstance(raw_lead, dict):
            raise ReplayError("TRADE_LEAD.SNAPSHOT payload must contain lead object")
        lead = TradeLead.from_dict(raw_lead)
        if lead.lead_id != event.aggregate_id:
            raise ReplayError("event aggregate_id does not match replayed lead_id")
        try:
            state.book.ingest(lead)
        except LeadConflictError as exc:
            raise ReplayError("journal contains conflicting TradeLead history") from exc
        return state

    def snapshot(self, state: TradeLeadReplayState) -> dict[str, Any]:
        leads = [lead.to_dict() for lead in state.book.all()]
        return {"projection": "TRADE_LEAD_BOOK_V1", "leads": leads}

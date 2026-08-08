"""Platform-foundation domain services for Phase 02B."""

from .event_journal import (
    JournalConflictError,
    JournalError,
    JournalIntegrityError,
    JournalRecord,
    SQLiteEventJournal,
)
from .events import DomainEvent, EventContractError
from .replay import ReplayEngine, ReplayError, TradeLeadProjector, trade_lead_snapshot_event

__all__ = [
    "DomainEvent",
    "EventContractError",
    "JournalConflictError",
    "JournalError",
    "JournalIntegrityError",
    "JournalRecord",
    "SQLiteEventJournal",
    "ReplayEngine",
    "ReplayError",
    "TradeLeadProjector",
    "trade_lead_snapshot_event",
]

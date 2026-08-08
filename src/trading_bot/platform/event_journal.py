"""Append-only SQLite event journal with deterministic cryptographic hash chain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Iterable

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.events import DomainEvent, EventContractError, canonical_json


GENESIS_HASH = "0" * 64


class JournalError(RuntimeError):
    """Base journal failure."""


class JournalConflictError(JournalError):
    """Same event ID was observed with conflicting immutable content."""


class JournalIntegrityError(JournalError):
    """Persisted journal does not satisfy append-only/hash-chain invariants."""


@dataclass(frozen=True, slots=True)
class JournalRecord:
    sequence: int
    event: DomainEvent
    recorded_at: datetime
    previous_chain_hash: str
    chain_hash: str

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise JournalIntegrityError("journal sequence must be positive")
        object.__setattr__(self, "recorded_at", require_aware(self.recorded_at, "recorded_at"))
        if self.recorded_at < self.event.occurred_at:
            raise JournalIntegrityError("recorded_at cannot precede event occurred_at")
        for name in ("previous_chain_hash", "chain_hash"):
            value = getattr(self, name)
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise JournalIntegrityError(f"{name} must be SHA-256 hex")

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event": self.event.to_dict(),
            "recorded_at": self.recorded_at.isoformat(),
            "previous_chain_hash": self.previous_chain_hash,
            "chain_hash": self.chain_hash,
        }


def _chain_hash(*, sequence: int, event_id: str, recorded_at: datetime, previous_hash: str) -> str:
    payload = {
        "sequence": sequence,
        "event_id": event_id,
        "recorded_at": require_aware(recorded_at, "recorded_at").isoformat(),
        "previous_chain_hash": previous_hash,
    }
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class SQLiteEventJournal:
    """Small local event store used by research/simulation runtime.

    SQLite triggers make UPDATE and DELETE fail at the storage layer.  A SHA-256
    chain additionally detects direct/offline tampering or accidental corruption.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = FULL")
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS journal_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                causation_id TEXT,
                producer TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                previous_chain_hash TEXT NOT NULL,
                chain_hash TEXT NOT NULL UNIQUE
            );
            CREATE INDEX IF NOT EXISTS ix_journal_aggregate
                ON journal_events (aggregate_type, aggregate_id, sequence);
            CREATE INDEX IF NOT EXISTS ix_journal_correlation
                ON journal_events (correlation_id, sequence);
            CREATE TRIGGER IF NOT EXISTS journal_no_update
                BEFORE UPDATE ON journal_events
                BEGIN
                    SELECT RAISE(ABORT, 'append-only journal: UPDATE forbidden');
                END;
            CREATE TRIGGER IF NOT EXISTS journal_no_delete
                BEFORE DELETE ON journal_events
                BEGIN
                    SELECT RAISE(ABORT, 'append-only journal: DELETE forbidden');
                END;
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteEventJournal":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS n FROM journal_events").fetchone()
        assert row is not None
        return int(row["n"])

    @property
    def head_hash(self) -> str:
        row = self._connection.execute(
            "SELECT chain_hash FROM journal_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        return GENESIS_HASH if row is None else str(row["chain_hash"])

    def append(self, event: DomainEvent, *, recorded_at: datetime) -> JournalRecord:
        recorded = require_aware(recorded_at, "recorded_at")
        if recorded < event.occurred_at:
            raise JournalError("recorded_at cannot precede event occurred_at")

        with self._connection:
            existing = self._connection.execute(
                "SELECT * FROM journal_events WHERE event_id = ?", (event.event_id,)
            ).fetchone()
            if existing is not None:
                record = self._row_to_record(existing)
                if record.event.to_dict() != event.to_dict():
                    raise JournalConflictError("same event_id has conflicting immutable content")
                return record

            if event.causation_id is not None:
                cause = self._connection.execute(
                    "SELECT sequence, correlation_id FROM journal_events WHERE event_id = ?",
                    (event.causation_id,),
                ).fetchone()
                if cause is None:
                    raise JournalError("causation_id must reference a previously journaled event")
                if str(cause["correlation_id"]) != event.correlation_id:
                    raise JournalError("caused event must retain its causation event correlation_id")

            previous = self._connection.execute(
                "SELECT sequence, chain_hash FROM journal_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = GENESIS_HASH if previous is None else str(previous["chain_hash"])
            expected_sequence = 1 if previous is None else int(previous["sequence"]) + 1
            chain_hash = _chain_hash(
                sequence=expected_sequence,
                event_id=event.event_id,
                recorded_at=recorded,
                previous_hash=previous_hash,
            )
            cursor = self._connection.execute(
                """
                INSERT INTO journal_events (
                    event_id,event_type,aggregate_type,aggregate_id,occurred_at,recorded_at,
                    correlation_id,causation_id,producer,schema_version,payload_json,
                    previous_chain_hash,chain_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.aggregate_type,
                    event.aggregate_id,
                    event.occurred_at.isoformat(),
                    recorded.isoformat(),
                    event.correlation_id,
                    event.causation_id,
                    event.producer,
                    event.schema_version,
                    event.payload_json,
                    previous_hash,
                    chain_hash,
                ),
            )
            if int(cursor.lastrowid) != expected_sequence:
                raise JournalIntegrityError("journal sequence is not contiguous")
            row = self._connection.execute(
                "SELECT * FROM journal_events WHERE sequence = ?", (expected_sequence,)
            ).fetchone()
            assert row is not None
            return self._row_to_record(row)

    def append_many(
        self,
        events: Iterable[tuple[DomainEvent, datetime]],
    ) -> tuple[JournalRecord, ...]:
        # append() is transaction-safe and idempotent.  This method deliberately
        # preserves input order, which becomes the authoritative journal order.
        return tuple(self.append(event, recorded_at=recorded_at) for event, recorded_at in events)

    def records(
        self,
        *,
        after_sequence: int = 0,
        through_sequence: int | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
        correlation_id: str | None = None,
    ) -> tuple[JournalRecord, ...]:
        if after_sequence < 0:
            raise JournalError("after_sequence cannot be negative")
        clauses = ["sequence > ?"]
        params: list[object] = [after_sequence]
        if through_sequence is not None:
            if through_sequence < after_sequence:
                raise JournalError("through_sequence cannot precede after_sequence")
            clauses.append("sequence <= ?")
            params.append(through_sequence)
        if aggregate_type is not None:
            clauses.append("aggregate_type = ?")
            params.append(aggregate_type)
        if aggregate_id is not None:
            if aggregate_type is None:
                raise JournalError("aggregate_id filter requires aggregate_type")
            clauses.append("aggregate_id = ?")
            params.append(aggregate_id)
        if correlation_id is not None:
            clauses.append("correlation_id = ?")
            params.append(correlation_id)
        sql = "SELECT * FROM journal_events WHERE " + " AND ".join(clauses) + " ORDER BY sequence"
        rows = self._connection.execute(sql, params).fetchall()
        return tuple(self._row_to_record(row) for row in rows)

    def get_by_event_id(self, event_id: str) -> JournalRecord | None:
        row = self._connection.execute(
            "SELECT * FROM journal_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return None if row is None else self._row_to_record(row)

    def verify_integrity(self) -> str:
        rows = self._connection.execute("SELECT * FROM journal_events ORDER BY sequence").fetchall()
        previous_hash = GENESIS_HASH
        expected_sequence = 1
        prior_event_ids: set[str] = set()
        correlation_by_event: dict[str, str] = {}
        for row in rows:
            record = self._row_to_record(row)
            if record.sequence != expected_sequence:
                raise JournalIntegrityError(
                    f"non-contiguous journal sequence {record.sequence}; expected {expected_sequence}"
                )
            if record.previous_chain_hash != previous_hash:
                raise JournalIntegrityError(f"previous-chain hash mismatch at sequence {record.sequence}")
            expected_chain = _chain_hash(
                sequence=record.sequence,
                event_id=record.event.event_id,
                recorded_at=record.recorded_at,
                previous_hash=previous_hash,
            )
            if record.chain_hash != expected_chain:
                raise JournalIntegrityError(f"chain hash mismatch at sequence {record.sequence}")
            if record.event.causation_id is not None:
                if record.event.causation_id not in prior_event_ids:
                    raise JournalIntegrityError(
                        f"causation points forward/missing at sequence {record.sequence}"
                    )
                if correlation_by_event[record.event.causation_id] != record.event.correlation_id:
                    raise JournalIntegrityError(
                        f"causation correlation mismatch at sequence {record.sequence}"
                    )
            prior_event_ids.add(record.event.event_id)
            correlation_by_event[record.event.event_id] = record.event.correlation_id
            previous_hash = record.chain_hash
            expected_sequence += 1
        return previous_hash

    def export_jsonl(self) -> str:
        return "\n".join(
            json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            for record in self.records()
        )

    def _row_to_record(self, row: sqlite3.Row) -> JournalRecord:
        payload = json.loads(str(row["payload_json"]))
        if not isinstance(payload, dict):
            raise JournalIntegrityError("persisted payload must be a JSON object")
        try:
            event = DomainEvent.from_dict(
                {
                    "event_id": row["event_id"],
                    "event_type": row["event_type"],
                    "aggregate_type": row["aggregate_type"],
                    "aggregate_id": row["aggregate_id"],
                    "occurred_at": row["occurred_at"],
                    "correlation_id": row["correlation_id"],
                    "causation_id": row["causation_id"],
                    "producer": row["producer"],
                    "schema_version": row["schema_version"],
                    "payload": payload,
                }
            )
        except (EventContractError, ValueError) as exc:
            raise JournalIntegrityError("persisted event content is invalid or tampered") from exc
        return JournalRecord(
            sequence=int(row["sequence"]),
            event=event,
            recorded_at=datetime.fromisoformat(str(row["recorded_at"])),
            previous_chain_hash=str(row["previous_chain_hash"]),
            chain_hash=str(row["chain_hash"]),
        )

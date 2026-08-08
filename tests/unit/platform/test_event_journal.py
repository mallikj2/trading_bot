from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

import pytest

from trading_bot.platform.event_journal import (
    GENESIS_HASH,
    JournalError,
    JournalIntegrityError,
    SQLiteEventJournal,
)
from trading_bot.platform.events import DomainEvent, EventContractError

UTC = timezone.utc
NOW = datetime(2026, 8, 8, 20, 0, tzinfo=UTC)


def event(*, suffix: str = "A", causation_id: str | None = None, correlation_id: str = "corr-1") -> DomainEvent:
    return DomainEvent.create(
        event_type="TEST.EVENT",
        aggregate_type="TEST",
        aggregate_id=f"aggregate-{suffix}",
        occurred_at=NOW,
        correlation_id=correlation_id,
        causation_id=causation_id,
        producer="test_suite",
        payload={"symbol": suffix, "value": "12.50", "nested": {"b": 2, "a": 1}},
    )


def test_event_id_is_deterministic_under_payload_key_order() -> None:
    first = DomainEvent.create(
        event_type="TEST.EVENT",
        aggregate_type="TEST",
        aggregate_id="one",
        occurred_at=NOW,
        correlation_id="corr",
        producer="tests",
        payload={"b": 2, "a": 1},
    )
    second = DomainEvent.create(
        event_type="TEST.EVENT",
        aggregate_type="TEST",
        aggregate_id="one",
        occurred_at=NOW,
        correlation_id="corr",
        producer="tests",
        payload={"a": 1, "b": 2},
    )
    assert first.event_id == second.event_id
    assert first.payload_json == second.payload_json


def test_event_rejects_float_payloads() -> None:
    with pytest.raises(EventContractError, match="float"):
        DomainEvent.create(
            event_type="TEST.EVENT",
            aggregate_type="TEST",
            aggregate_id="one",
            occurred_at=NOW,
            correlation_id="corr",
            producer="tests",
            payload={"ratio": 0.1},
        )


def test_event_normalizes_timestamp_to_utc() -> None:
    eastern = timezone(timedelta(hours=-4))
    item = DomainEvent.create(
        event_type="TEST.EVENT",
        aggregate_type="TEST",
        aggregate_id="one",
        occurred_at=datetime(2026, 8, 8, 16, 0, tzinfo=eastern),
        correlation_id="corr",
        producer="tests",
        payload={},
    )
    assert item.occurred_at == NOW


def test_event_from_dict_detects_tampered_event_id() -> None:
    item = event()
    raw = item.to_dict()
    raw["event_id"] = "0" * 64
    with pytest.raises(EventContractError, match="event_id"):
        DomainEvent.from_dict(raw)


def test_journal_append_is_idempotent() -> None:
    item = event()
    journal = SQLiteEventJournal()
    first = journal.append(item, recorded_at=NOW + timedelta(seconds=1))
    second = journal.append(item, recorded_at=NOW + timedelta(minutes=2))
    assert first == second
    assert journal.count == 1
    assert journal.verify_integrity() == first.chain_hash


def test_journal_requires_cause_to_exist_first() -> None:
    root = event()
    child = event(suffix="B", causation_id=root.event_id)
    journal = SQLiteEventJournal()
    with pytest.raises(JournalError, match="causation_id"):
        journal.append(child, recorded_at=NOW + timedelta(seconds=1))


def test_journal_requires_correlation_continuity_for_causation() -> None:
    root = event(correlation_id="corr-A")
    child = event(suffix="B", causation_id=root.event_id, correlation_id="corr-B")
    journal = SQLiteEventJournal()
    journal.append(root, recorded_at=NOW + timedelta(seconds=1))
    with pytest.raises(JournalError, match="correlation_id"):
        journal.append(child, recorded_at=NOW + timedelta(seconds=2))


def test_recorded_at_cannot_precede_occurrence() -> None:
    journal = SQLiteEventJournal()
    with pytest.raises(JournalError, match="precede"):
        journal.append(event(), recorded_at=NOW - timedelta(seconds=1))


def test_journal_is_storage_level_append_only() -> None:
    journal = SQLiteEventJournal()
    record = journal.append(event(), recorded_at=NOW + timedelta(seconds=1))
    with pytest.raises(sqlite3.DatabaseError, match="UPDATE forbidden"):
        journal._connection.execute(
            "UPDATE journal_events SET producer='tampered' WHERE sequence=?", (record.sequence,)
        )
    with pytest.raises(sqlite3.DatabaseError, match="DELETE forbidden"):
        journal._connection.execute("DELETE FROM journal_events WHERE sequence=?", (record.sequence,))


def test_journal_detects_offline_tampering(tmp_path: Path) -> None:
    path = tmp_path / "events.sqlite3"
    journal = SQLiteEventJournal(path)
    journal.append(event(), recorded_at=NOW + timedelta(seconds=1))
    journal.close()

    raw = sqlite3.connect(path)
    raw.execute("DROP TRIGGER journal_no_update")
    raw.execute("UPDATE journal_events SET payload_json=? WHERE sequence=1", (json.dumps({"bad": True}),))
    raw.commit()
    raw.close()

    reopened = SQLiteEventJournal(path)
    with pytest.raises(JournalIntegrityError, match="tampered"):
        reopened.verify_integrity()


def test_journal_persists_and_reopens_with_same_head_hash(tmp_path: Path) -> None:
    path = tmp_path / "events.sqlite3"
    journal = SQLiteEventJournal(path)
    root = event()
    root_record = journal.append(root, recorded_at=NOW + timedelta(seconds=1))
    child = event(suffix="B", causation_id=root.event_id)
    child_record = journal.append(child, recorded_at=NOW + timedelta(seconds=2))
    head = journal.head_hash
    assert root_record.previous_chain_hash == GENESIS_HASH
    assert child_record.previous_chain_hash == root_record.chain_hash
    journal.close()

    reopened = SQLiteEventJournal(path)
    assert reopened.count == 2
    assert reopened.head_hash == head
    assert reopened.verify_integrity() == head


def test_journal_filters_aggregate_and_correlation() -> None:
    journal = SQLiteEventJournal()
    root = event(suffix="A", correlation_id="corr-A")
    other = event(suffix="B", correlation_id="corr-B")
    journal.append(root, recorded_at=NOW + timedelta(seconds=1))
    journal.append(other, recorded_at=NOW + timedelta(seconds=2))
    assert [r.event.aggregate_id for r in journal.records(aggregate_type="TEST", aggregate_id="aggregate-B")] == ["aggregate-B"]
    assert [r.event.aggregate_id for r in journal.records(correlation_id="corr-A")] == ["aggregate-A"]
    with pytest.raises(JournalError, match="aggregate_id"):
        journal.records(aggregate_id="aggregate-A")


def test_jsonl_export_is_deterministic() -> None:
    journal = SQLiteEventJournal()
    journal.append(event(), recorded_at=NOW + timedelta(seconds=1))
    first = journal.export_jsonl()
    second = journal.export_jsonl()
    assert first == second
    assert json.loads(first)["sequence"] == 1

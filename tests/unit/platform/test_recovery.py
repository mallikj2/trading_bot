from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.orders import OrderIntent, OrderPurpose, OrderSide, OrderState, OrderType, TimeInForce
from trading_bot.platform.recovery import (
    BrokerAccountSnapshot,
    FindingDisposition,
    RecoveryContractError,
    RecoveryCoordinator,
    RecoveryFindingCode,
)
from trading_bot.platform.runtime_safety import RuntimeSafetyState
from trading_bot.platform.simulated_broker import OMSService, SimulatedBroker

UTC = timezone.utc
T0 = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)


def make_intent(*, suffix: str = "1", qty: int = 3, side: OrderSide = OrderSide.BUY) -> OrderIntent:
    return OrderIntent.create(
        source_lead_id=f"lead-{suffix}",
        source_lead_hash=(suffix * 64)[:64],
        instrument_id=UUID(f"11111111-2222-3333-4444-55555555555{suffix}"),
        symbol=f"T{suffix}",
        side=side,
        purpose=OrderPurpose.INCREASE_EXPOSURE,
        quantity=qty,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        created_at=T0,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        decision_at=T0 - timedelta(minutes=30),
    )


def ready_order(journal: SQLiteEventJournal, broker: SimulatedBroker, intent: OrderIntent) -> OMSService:
    oms = OMSService(journal=journal, broker=broker)
    oms.create(intent)
    oms.approve_risk(intent.order_id, approved_at=T0 + timedelta(seconds=1))
    return oms


def codes(report) -> set[RecoveryFindingCode]:
    return {finding.code for finding in report.findings}


def test_future_snapshot_is_rejected(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "future.sqlite")
    broker = SimulatedBroker()
    snap = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=1))
    with pytest.raises(RecoveryContractError, match="future broker snapshot"):
        RecoveryCoordinator(journal=journal, broker=broker).run(snap, started_at=T0)
    journal.close()


def test_crash_after_broker_acceptance_recovers_without_resubmit(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "crash.sqlite")
    broker = SimulatedBroker()
    intent = make_intent()
    oms = ready_order(journal, broker, intent)
    assert oms.stage_submission(intent.order_id, submitted_at=T0 + timedelta(seconds=2)).state == OrderState.SUBMITTED
    broker.submit(intent, submitted_at=T0 + timedelta(seconds=2))
    assert broker.submission_count(intent.order_id) == 1

    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=3))
    report = RecoveryCoordinator(journal=journal, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=4))
    assert RecoveryFindingCode.CRASH_AFTER_SUBMISSION in codes(report)
    assert report.unresolved_count == 0
    assert report.final_runtime_state == RuntimeSafetyState.ACTIVE
    assert broker.submission_count(intent.order_id) == 1
    assert OMSService(journal=journal, broker=broker).projector.get(intent.order_id).state == OrderState.ACKNOWLEDGED
    journal.close()


def test_missed_partial_fill_is_imported_once(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "missed.sqlite")
    broker = SimulatedBroker()
    intent = make_intent(qty=3)
    oms = ready_order(journal, broker, intent)
    oms.submit(intent.order_id, submitted_at=T0 + timedelta(seconds=2))
    broker.fill(intent.order_id, quantity=1, price="100", occurred_at=T0 + timedelta(seconds=3), execution_id="missed-1")
    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=4))

    report = RecoveryCoordinator(journal=journal, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=5))
    assert RecoveryFindingCode.MISSED_BROKER_FILL in codes(report)
    recovered = OMSService(journal=journal, broker=broker).projector.get(intent.order_id)
    assert recovered.state == OrderState.PARTIALLY_FILLED
    assert recovered.filled_quantity == 1
    assert [fill.execution_id for fill in recovered.fills] == ["missed-1"]
    assert report.unresolved_count == 0
    journal.close()


def test_external_order_unknown_locally_halts_and_is_not_imported(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "external.sqlite")
    broker = SimulatedBroker()
    intent = make_intent()
    broker.submit(intent, submitted_at=T0)
    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=1))
    report = RecoveryCoordinator(journal=journal, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=2))
    assert RecoveryFindingCode.EXTERNAL_ORDER_UNKNOWN_LOCALLY in codes(report)
    assert report.final_runtime_state == RuntimeSafetyState.HALTED
    assert report.unresolved_count >= 1
    assert OMSService(journal=journal, broker=broker).projector.snapshots() == ()
    journal.close()


def test_local_open_order_absent_externally_halts_without_resubmit(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "missing.sqlite")
    local_broker = SimulatedBroker()
    intent = make_intent()
    oms = ready_order(journal, local_broker, intent)
    oms.stage_submission(intent.order_id, submitted_at=T0 + timedelta(seconds=2))
    empty_external = SimulatedBroker()
    snapshot = BrokerAccountSnapshot.from_broker(empty_external, captured_at=T0 + timedelta(seconds=3))
    report = RecoveryCoordinator(journal=journal, broker=empty_external).run(snapshot, started_at=T0 + timedelta(seconds=4))
    assert RecoveryFindingCode.LOCAL_ORDER_ABSENT_EXTERNALLY in codes(report)
    assert report.final_runtime_state == RuntimeSafetyState.HALTED
    assert empty_external.submission_count(intent.order_id) == 0
    journal.close()


def test_position_mismatch_halts(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "position.sqlite")
    broker = SimulatedBroker()
    instrument_id = str(make_intent().instrument_id)
    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0).with_positions({instrument_id: 5})
    report = RecoveryCoordinator(journal=journal, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=1))
    assert RecoveryFindingCode.POSITION_QUANTITY_MISMATCH in codes(report)
    assert report.final_runtime_state == RuntimeSafetyState.HALTED
    journal.close()


def test_duplicate_broker_execution_is_not_double_counted(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "duplicate.sqlite")
    broker = SimulatedBroker()
    intent = make_intent(qty=3)
    oms = ready_order(journal, broker, intent)
    oms.submit(intent.order_id, submitted_at=T0 + timedelta(seconds=2))
    oms.apply_fill(intent.order_id, quantity=1, price="100", occurred_at=T0 + timedelta(seconds=3), execution_id="exec-1")
    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=4)).with_duplicate_execution(intent.order_id)
    report = RecoveryCoordinator(journal=journal, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=5))
    assert RecoveryFindingCode.DUPLICATE_BROKER_EXECUTION in codes(report)
    assert report.final_runtime_state == RuntimeSafetyState.HALTED
    recovered = OMSService(journal=journal, broker=broker).projector.get(intent.order_id)
    assert recovered.filled_quantity == 1
    assert len(recovered.fills) == 1
    journal.close()


def test_stale_startup_snapshot_halts_before_order_repair(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "stale.sqlite")
    broker = SimulatedBroker()
    snap = BrokerAccountSnapshot.from_broker(broker, captured_at=T0)
    report = RecoveryCoordinator(journal=journal, broker=broker, max_snapshot_age=timedelta(seconds=30)).run(
        snap, started_at=T0 + timedelta(seconds=31)
    )
    assert codes(report) == {RecoveryFindingCode.STALE_STARTUP_SNAPSHOT}
    assert report.final_runtime_state == RuntimeSafetyState.HALTED
    journal.close()


def test_repaired_finding_is_marked_auto_repaired(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "disposition.sqlite")
    broker = SimulatedBroker()
    intent = make_intent()
    oms = ready_order(journal, broker, intent)
    oms.stage_submission(intent.order_id, submitted_at=T0 + timedelta(seconds=2))
    broker.submit(intent, submitted_at=T0 + timedelta(seconds=2))
    snap = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=3))
    report = RecoveryCoordinator(journal=journal, broker=broker).run(snap, started_at=T0 + timedelta(seconds=4))
    finding = next(item for item in report.findings if item.code == RecoveryFindingCode.CRASH_AFTER_SUBMISSION)
    assert finding.disposition == FindingDisposition.AUTO_REPAIRED
    journal.close()

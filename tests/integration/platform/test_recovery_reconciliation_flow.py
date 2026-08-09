from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from trading_bot.platform.alerts import AlertIncidentCenter
from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.orders import OrderIntent, OrderPurpose, OrderSide, OrderState, OrderType, TimeInForce
from trading_bot.platform.recovery import BrokerAccountSnapshot, RecoveryCoordinator, RecoveryFindingCode
from trading_bot.platform.runtime_safety import RuntimeSafetyProjector, RuntimeSafetyState
from trading_bot.platform.simulated_broker import OMSService, SimulatedBroker

UTC = timezone.utc
T0 = datetime(2026, 8, 8, 15, 0, tzinfo=UTC)


def intent() -> OrderIntent:
    return OrderIntent.create(
        source_lead_id="lead-pf10",
        source_lead_hash="a" * 64,
        instrument_id=UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        symbol="REC",
        side=OrderSide.BUY,
        purpose=OrderPurpose.INCREASE_EXPOSURE,
        quantity=2,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        created_at=T0,
        strategy_id="CSMOM-LS",
        strategy_version="v0.2",
        decision_at=T0 - timedelta(minutes=30),
    )


def test_crash_recovery_survives_process_restart_with_identical_state(tmp_path: Path) -> None:
    path = tmp_path / "restart.sqlite"
    broker = SimulatedBroker()
    journal = SQLiteEventJournal(path)
    order = intent()
    oms = OMSService(journal=journal, broker=broker)
    oms.create(order)
    oms.approve_risk(order.order_id, approved_at=T0 + timedelta(seconds=1))
    oms.stage_submission(order.order_id, submitted_at=T0 + timedelta(seconds=2))
    broker.submit(order, submitted_at=T0 + timedelta(seconds=2))
    broker.fill(order.order_id, quantity=1, price="101", occurred_at=T0 + timedelta(seconds=3), execution_id="external-fill-1")
    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=4))
    journal.close()

    reopened = SQLiteEventJournal(path)
    report = RecoveryCoordinator(journal=reopened, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=5))
    state_hash = OMSService(journal=reopened, broker=broker).projector.state_hash
    journal_head = reopened.head_hash
    reopened.verify_integrity()
    reopened.close()

    second = SQLiteEventJournal(path)
    assert OMSService(journal=second, broker=broker).projector.state_hash == state_hash
    assert second.head_hash == journal_head
    assert report.duplicate_risk_created is False
    assert broker.submission_count(order.order_id) == 1
    assert {f.code for f in report.findings} >= {
        RecoveryFindingCode.CRASH_AFTER_SUBMISSION,
        RecoveryFindingCode.MISSED_BROKER_FILL,
    }
    assert OMSService(journal=second, broker=broker).projector.get(order.order_id).state == OrderState.PARTIALLY_FILLED
    second.close()


def test_unresolved_external_order_generates_incident_and_halt_event(tmp_path: Path) -> None:
    path = tmp_path / "incident.sqlite"
    journal = SQLiteEventJournal(path)
    broker = SimulatedBroker()
    external = intent()
    broker.submit(external, submitted_at=T0)
    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=1))
    report = RecoveryCoordinator(journal=journal, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=2))
    assert report.final_runtime_state == RuntimeSafetyState.HALTED

    event_types = [record.event.event_type for record in journal.records()]
    assert "RECOVERY.STARTED" in event_types
    assert "RECOVERY.FINDING" in event_types
    assert "INCIDENT.OPENED" in event_types
    assert "ALERT.RAISED" in event_types
    assert "PROTECTION.EVALUATED" in event_types
    assert "RUNTIME_SAFETY.TRANSITION" in event_types
    assert "RECOVERY.COMPLETED" in event_types
    center = AlertIncidentCenter(journal)
    assert center.summary()["open_incident_count"] == 1
    journal.close()


def test_repaired_reconciliation_incident_is_resolved(tmp_path: Path) -> None:
    journal = SQLiteEventJournal(tmp_path / "resolved.sqlite")
    broker = SimulatedBroker()
    order = intent()
    oms = OMSService(journal=journal, broker=broker)
    oms.create(order)
    oms.approve_risk(order.order_id, approved_at=T0 + timedelta(seconds=1))
    oms.stage_submission(order.order_id, submitted_at=T0 + timedelta(seconds=2))
    broker.submit(order, submitted_at=T0 + timedelta(seconds=2))
    snapshot = BrokerAccountSnapshot.from_broker(broker, captured_at=T0 + timedelta(seconds=3))
    report = RecoveryCoordinator(journal=journal, broker=broker).run(snapshot, started_at=T0 + timedelta(seconds=4))
    assert report.unresolved_count == 0
    center = AlertIncidentCenter(journal)
    assert center.summary()["resolved_incident_count"] == 1
    assert center.summary()["active_incident_count"] == 0
    journal.close()

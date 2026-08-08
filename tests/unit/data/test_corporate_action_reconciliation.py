from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from trading_bot.data.contracts import CorporateAction, CorporateActionType
from trading_bot.data.corporate_action_reconciliation import (
    EvidenceStatus,
    ProviderCorporateActionEvidence,
    ReconciliationStatus,
    reconcile_action_set,
    reconcile_corporate_action,
)

UTC = timezone.utc
IID = UUID("00000000-0000-0000-0000-000000000001")
CHILD = UUID("00000000-0000-0000-0000-000000000002")


def dt(day: int) -> datetime:
    return datetime(2024, 6, day, 20, tzinfo=UTC)


def test_split_reconciliation_passes():
    action = CorporateAction(
        action_id="split-1", instrument_id=IID, action_type=CorporateActionType.SPLIT,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="kernel",
        split_old_shares=Decimal("1"), split_new_shares=Decimal("10"),
    )
    evidence = ProviderCorporateActionEvidence(
        provider="EDI", provider_event_id="e1", action_type=CorporateActionType.SPLIT,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="edi",
        share_multiplier=Decimal("10"),
    )
    assert reconcile_corporate_action(action, evidence).status == ReconciliationStatus.PASS


def test_split_ratio_mismatch_fails():
    action = CorporateAction(
        action_id="split-1", instrument_id=IID, action_type=CorporateActionType.SPLIT,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="kernel",
        split_old_shares=Decimal("1"), split_new_shares=Decimal("10"),
    )
    evidence = ProviderCorporateActionEvidence(
        provider="EDI", provider_event_id="e1", action_type=CorporateActionType.SPLIT,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="edi",
        share_multiplier=Decimal("4"),
    )
    result = reconcile_corporate_action(action, evidence)
    assert result.status == ReconciliationStatus.MISMATCH
    assert "share multiplier mismatch" in result.reasons


def test_spinoff_ratio_and_outturn_are_checked():
    action = CorporateAction(
        action_id="spin-1", instrument_id=IID, action_type=CorporateActionType.SPINOFF,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="kernel",
        stock_ratio=Decimal("0.2"), child_instrument_id=CHILD,
    )
    evidence = ProviderCorporateActionEvidence(
        provider="EDI", provider_event_id="e2", action_type=CorporateActionType.SPINOFF,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="edi",
        stock_ratio=Decimal("0.2"), outturn_identifier="US1234567890",
    )
    assert reconcile_corporate_action(action, evidence, expected_outturn_identifier="US1234567890").status == ReconciliationStatus.PASS
    assert reconcile_corporate_action(action, evidence, expected_outturn_identifier="US0000000000").status == ReconciliationStatus.MISMATCH


def test_zero_recovery_terminal_action_is_explicit():
    action = CorporateAction(
        action_id="bk-1", instrument_id=IID, action_type=CorporateActionType.BANKRUPTCY,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="kernel",
        cash_amount=Decimal("0"), currency="USD",
    )
    evidence = ProviderCorporateActionEvidence(
        provider="EDI", provider_event_id="e3", action_type=CorporateActionType.BANKRUPTCY,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="edi",
        cash_amount=Decimal("0"), currency="USD",
    )
    assert reconcile_corporate_action(action, evidence).status == ReconciliationStatus.PASS


def test_missing_provider_evidence_blocks_action_set():
    action = CorporateAction(
        action_id="cash-1", instrument_id=IID, action_type=CorporateActionType.CASH_DIVIDEND,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="kernel",
        cash_amount=Decimal("1.00"), currency="USD",
    )
    result = reconcile_action_set([action], [])[0]
    assert result.status == ReconciliationStatus.BLOCKED


def test_conflicting_latest_provider_revision_blocks():
    action = CorporateAction(
        action_id="cash-1", instrument_id=IID, action_type=CorporateActionType.CASH_DIVIDEND,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="kernel",
        cash_amount=Decimal("1.00"), currency="USD",
    )
    rows = [
        ProviderCorporateActionEvidence(
            provider="EDI", provider_event_id="e4", action_type=CorporateActionType.CASH_DIVIDEND,
            effective_at=dt(10), available_at=dt(9), source_snapshot_id="a",
            cash_amount=Decimal("1.00"), currency="USD", revision=1,
        ),
        ProviderCorporateActionEvidence(
            provider="EDI", provider_event_id="e4", action_type=CorporateActionType.CASH_DIVIDEND,
            effective_at=dt(10), available_at=dt(9), source_snapshot_id="b",
            cash_amount=Decimal("2.00"), currency="USD", revision=1,
        ),
    ]
    assert reconcile_action_set([action], rows)[0].status == ReconciliationStatus.BLOCKED


def test_cancelled_provider_evidence_does_not_reconcile_to_active_action():
    action = CorporateAction(
        action_id="cash-1", instrument_id=IID, action_type=CorporateActionType.CASH_DIVIDEND,
        effective_at=dt(10), available_at=dt(10), source_snapshot_id="kernel",
        cash_amount=Decimal("1.00"), currency="USD",
    )
    evidence = ProviderCorporateActionEvidence(
        provider="EDI", provider_event_id="e5", action_type=CorporateActionType.CASH_DIVIDEND,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="edi",
        cash_amount=Decimal("1.00"), currency="USD", status=EvidenceStatus.CANCELLED,
    )
    assert reconcile_corporate_action(action, evidence).status == ReconciliationStatus.MISMATCH


def test_future_provider_revision_is_invisible_at_decision_cutoff():
    action = CorporateAction(
        action_id="cash-pit", instrument_id=IID, action_type=CorporateActionType.CASH_DIVIDEND,
        effective_at=dt(10), available_at=dt(8), source_snapshot_id="kernel",
        cash_amount=Decimal("1.00"), currency="USD",
    )
    rows = [
        ProviderCorporateActionEvidence(
            provider="EDI", provider_event_id="pit-1", action_type=CorporateActionType.CASH_DIVIDEND,
            effective_at=dt(10), available_at=dt(8), source_snapshot_id="old",
            cash_amount=Decimal("1.00"), currency="USD", revision=0,
        ),
        ProviderCorporateActionEvidence(
            provider="EDI", provider_event_id="pit-1", action_type=CorporateActionType.CASH_DIVIDEND,
            effective_at=dt(10), available_at=dt(12), source_snapshot_id="future",
            cash_amount=Decimal("2.00"), currency="USD", revision=1,
        ),
    ]
    result = reconcile_action_set([action], rows, decision_at=dt(9))[0]
    assert result.status == ReconciliationStatus.PASS


def test_multiple_distinct_same_day_provider_events_block_ambiguous_match():
    action = CorporateAction(
        action_id="cash-ambiguous", instrument_id=IID, action_type=CorporateActionType.CASH_DIVIDEND,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="kernel",
        cash_amount=Decimal("1.00"), currency="USD",
    )
    rows = [
        ProviderCorporateActionEvidence(
            provider="EDI", provider_event_id="event-a", action_type=CorporateActionType.CASH_DIVIDEND,
            effective_at=dt(10), available_at=dt(9), source_snapshot_id="a",
            cash_amount=Decimal("1.00"), currency="USD",
        ),
        ProviderCorporateActionEvidence(
            provider="EDI", provider_event_id="event-b", action_type=CorporateActionType.CASH_DIVIDEND,
            effective_at=dt(10), available_at=dt(9), source_snapshot_id="b",
            cash_amount=Decimal("1.00"), currency="USD",
        ),
    ]
    result = reconcile_action_set([action], rows, decision_at=dt(9))[0]
    assert result.status == ReconciliationStatus.BLOCKED
    assert "multiple distinct provider events" in result.reasons[0]


def test_spinoff_requires_provider_outturn_identifier():
    action = CorporateAction(
        action_id="spin-missing-outturn", instrument_id=IID, action_type=CorporateActionType.SPINOFF,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="kernel",
        stock_ratio=Decimal("0.2"), child_instrument_id=CHILD,
    )
    evidence = ProviderCorporateActionEvidence(
        provider="EDI", provider_event_id="spin-no-child", action_type=CorporateActionType.SPINOFF,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="edi", stock_ratio=Decimal("0.2"),
    )
    result = reconcile_corporate_action(action, evidence)
    assert result.status == ReconciliationStatus.MISMATCH
    assert "spinoff outturn identifier missing" in result.reasons


def test_cash_merger_requires_currency_match():
    action = CorporateAction(
        action_id="merger-currency", instrument_id=IID, action_type=CorporateActionType.MERGER,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="kernel",
        cash_amount=Decimal("54.20"), currency="USD",
    )
    evidence = ProviderCorporateActionEvidence(
        provider="EDI", provider_event_id="merger-currency", action_type=CorporateActionType.MERGER,
        effective_at=dt(10), available_at=dt(9), source_snapshot_id="edi",
        cash_amount=Decimal("54.20"), currency="CAD",
    )
    result = reconcile_corporate_action(action, evidence)
    assert result.status == ReconciliationStatus.MISMATCH
    assert "merger cash currency mismatch" in result.reasons

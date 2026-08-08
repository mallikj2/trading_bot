from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from trading_bot.data.contracts import CorporateAction, CorporateActionType
from trading_bot.data.corporate_action_reconciliation import ProviderCorporateActionEvidence, ReconciliationStatus, reconcile_action_set

UTC = timezone.utc
IID = UUID("00000000-0000-0000-0000-000000000101")


def test_representative_split_and_cash_merger_reconcile_as_one_batch():
    split = CorporateAction(
        action_id="nvda", instrument_id=IID, action_type=CorporateActionType.SPLIT,
        effective_at=datetime(2024, 6, 10, 20, tzinfo=UTC), available_at=datetime(2024, 6, 10, 20, tzinfo=UTC),
        source_snapshot_id="kernel", split_old_shares=Decimal("1"), split_new_shares=Decimal("10"),
    )
    merger = CorporateAction(
        action_id="twtr", instrument_id=IID, action_type=CorporateActionType.MERGER,
        effective_at=datetime(2022, 10, 27, 20, tzinfo=UTC), available_at=datetime(2022, 10, 27, 20, tzinfo=UTC),
        source_snapshot_id="kernel", cash_amount=Decimal("54.20"), currency="USD",
    )
    evidence = [
        ProviderCorporateActionEvidence(
            provider="EDI_WCA", provider_event_id="s", action_type=CorporateActionType.SPLIT,
            effective_at=datetime(2024, 6, 10, 23, 59, tzinfo=UTC), available_at=datetime(2024, 5, 23, 20, tzinfo=UTC),
            source_snapshot_id="edi", share_multiplier=Decimal("10"),
        ),
        ProviderCorporateActionEvidence(
            provider="EDI_WCA", provider_event_id="m", action_type=CorporateActionType.MERGER,
            effective_at=datetime(2022, 10, 27, 23, 59, tzinfo=UTC), available_at=datetime(2022, 10, 27, 21, tzinfo=UTC),
            source_snapshot_id="edi", cash_amount=Decimal("54.20"), currency="USD",
        ),
    ]
    results = reconcile_action_set([split, merger], evidence)
    assert [result.status for result in results] == [ReconciliationStatus.PASS, ReconciliationStatus.PASS]

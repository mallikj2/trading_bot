from decimal import Decimal

from trading_bot.data.adapters.edi_corporate_actions import canonical_ratio, parse_edi_evidence
from trading_bot.data.contracts import CorporateActionType
from trading_bot.data.corporate_action_reconciliation import EvidenceStatus


def test_canonical_ratio_supports_both_provider_conventions():
    assert canonical_ratio(Decimal("1"), Decimal("10"), semantics="TOTAL_NEW_OVER_OLD") == Decimal("10")
    assert canonical_ratio(Decimal("5"), Decimal("1"), semantics="ADDITIONAL_NEW_OVER_OLD") == Decimal("1.2")


def test_parse_edi_split_uses_change_timestamp_as_availability():
    row = {
        "EvtUniqueID": "abc",
        "EvtChangeDT": "2024-05-23T15:10:00",
        "ExDT": "2024-06-10",
        "EventCD": "FSPLT",
        "EvtActionCD": "I",
        "RatioOld": "1",
        "RatioNew": "10",
    }
    evidence = parse_edi_evidence(
        row, action_type=CorporateActionType.SPLIT, source_snapshot_id="s1",
        ratio_semantics="TOTAL_NEW_OVER_OLD",
    )
    assert evidence.provider == "EDI_WCA"
    assert evidence.share_multiplier == Decimal("10")
    assert evidence.available_at.isoformat().startswith("2024-05-23T15:10:00")


def test_parse_edi_spinoff_additional_ratio_and_outturn():
    row = {
        "EventID": "spin",
        "EvtChangeDT": "2021-10-12T12:00:00",
        "EffectiveDT": "2021-11-03",
        "EventCD": "DMRGR",
        "RatioOld": "5",
        "RatioNew": "1",
        "OutIsin": "US50155Q1004",
    }
    evidence = parse_edi_evidence(
        row, action_type=CorporateActionType.SPINOFF, source_snapshot_id="s2",
        ratio_semantics="ADDITIONAL_NEW_OVER_OLD",
    )
    assert evidence.stock_ratio == Decimal("0.2")
    assert evidence.outturn_identifier == "US50155Q1004"


def test_parse_edi_cancellation_status():
    row = {
        "EventID": "div",
        "EvtChangeDT": "2024-01-02T12:00:00",
        "ExDT": "2024-02-01",
        "EvtActionCD": "C",
        "grossdividend": "1.00",
        "RateCurenCD": "USD",
    }
    evidence = parse_edi_evidence(row, action_type=CorporateActionType.CASH_DIVIDEND, source_snapshot_id="s3")
    assert evidence.status == EvidenceStatus.CANCELLED
    assert evidence.cash_amount == Decimal("1.00")

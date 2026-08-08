from decimal import Decimal

import pytest

from trading_bot.data.adapters.databento_corporate_actions import (
    DatabentoCorporateActionsClient,
    DatabentoCorporateActionsLicenseError,
    parse_databento_evidence,
)
from trading_bot.data.contracts import CorporateActionType


class FakeCorporateActions:
    def __init__(self):
        self.kwargs = None
    def get_range(self, **kwargs):
        self.kwargs = kwargs
        return [{"ok": True}]


class FakeReference:
    def __init__(self):
        self.corporate_actions = FakeCorporateActions()


def test_license_flag_is_required():
    with pytest.raises(DatabentoCorporateActionsLicenseError):
        DatabentoCorporateActionsClient(api_key="key", license_approved=False)


def test_get_range_forces_us_and_pit():
    ref = FakeReference()
    client = DatabentoCorporateActionsClient(api_key="key", license_approved=True, reference_factory=lambda _: ref)
    result = client.get_range(symbols=["NVDA"], start="2024-01-01", end="2024-12-31", events=["FSPLT"])
    assert result == [{"ok": True}]
    assert ref.corporate_actions.kwargs["countries"] == ["US"]
    assert ref.corporate_actions.kwargs["pit"] is True


def test_parse_databento_split_ratio():
    row = {
        "event_unique_id": "x",
        "ts_record": "2024-05-23T12:00:00+00:00",
        "ex_date": "2024-06-10",
        "event": "FSPLT",
        "ratio_old": "1",
        "ratio_new": "10",
    }
    evidence = parse_databento_evidence(row, action_type=CorporateActionType.SPLIT, source_snapshot_id="db")
    assert evidence.share_multiplier == Decimal("10")


def test_parse_databento_stock_dividend_ratio_is_incremental():
    row = {
        "event_unique_id": "x",
        "ts_record": "2024-01-01T12:00:00+00:00",
        "ex_date": "2024-02-01",
        "event": "FSPLT",
        "event_subtype": "DIV",
        "ratio_old": "1",
        "ratio_new": "1.1",
    }
    evidence = parse_databento_evidence(row, action_type=CorporateActionType.STOCK_DIVIDEND, source_snapshot_id="db")
    assert evidence.stock_ratio == Decimal("0.1")

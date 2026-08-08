from dataclasses import dataclass

import pytest

from trading_bot.data.adapters.databento_companion import (
    DatabentoCompanionClient,
    DatabentoLicenseError,
    dataframe_row_count,
)


class FakeSecurityMaster:
    def __init__(self):
        self.calls = []

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        return [{"symbol": "AAPL", "listing_status": "ACTIVE"}]


class FakeReference:
    def __init__(self):
        self.security_master = FakeSecurityMaster()


class FakeTimeseries:
    def __init__(self):
        self.calls = []

    def get_range(self, **kwargs):
        self.calls.append(kwargs)
        return [{"price": 100, "size": 10}, {"price": 101, "size": 20}]


class FakeHistorical:
    def __init__(self):
        self.timeseries = FakeTimeseries()


def test_license_gate_is_fail_closed(monkeypatch):
    monkeypatch.delenv("DATABENTO_RESEARCH_LICENSE_APPROVED", raising=False)
    with pytest.raises(DatabentoLicenseError):
        DatabentoCompanionClient(api_key="db-test", license_approved=False)


def test_security_master_range_uses_pit_effective_index():
    ref = FakeReference()
    client = DatabentoCompanionClient(
        api_key="db-test",
        license_approved=True,
        reference_factory=lambda _: ref,
        historical_factory=lambda _: FakeHistorical(),
    )
    rows = client.security_master_range(symbol="AAPL", start="2020-01-01", end="2020-02-01")
    assert dataframe_row_count(rows) == 1
    assert ref.security_master.calls[0]["index"] == "ts_effective"
    assert ref.security_master.calls[0]["countries"] == ["US"]
    assert ref.security_master.calls[0]["security_types"] == ["EQS"]


def test_historical_trades_requires_explicit_dataset_and_trade_schema():
    hist = FakeHistorical()
    client = DatabentoCompanionClient(
        api_key="db-test",
        license_approved=True,
        reference_factory=lambda _: FakeReference(),
        historical_factory=lambda _: hist,
    )
    rows = client.historical_trades(
        dataset="TEST.US.EQUITIES",
        symbol="AAPL",
        start="2025-01-02T15:00:00Z",
        end="2025-01-02T15:30:00Z",
    )
    assert dataframe_row_count(rows) == 2
    call = hist.timeseries.calls[0]
    assert call["schema"] == "trades"
    assert call["dataset"] == "TEST.US.EQUITIES"
    assert call["stype_in"] == "figi"

from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from trading_bot.data.adapters.ortex_borrow import (
    BorrowSourceLicenseError,
    OrtexBorrowClient,
    OrtexBorrowClientConfig,
)


class CaptureTransport:
    def __init__(self):
        self.urls = []
        self.headers = []

    def get_json(self, url, *, headers, timeout):
        self.urls.append(url)
        self.headers.append(dict(headers))
        return {"data": []}


def test_standard_research_use_requires_explicit_license_approval():
    with pytest.raises(BorrowSourceLicenseError):
        OrtexBorrowClientConfig(api_key="secret", research_license_approved=False)


def test_documented_test_key_can_be_used_only_in_demo_mode():
    cfg = OrtexBorrowClientConfig(api_key="TEST", demo_mode=True)
    assert cfg.demo_mode is True
    with pytest.raises(ValueError):
        OrtexBorrowClientConfig(api_key="not-test", demo_mode=True)


def test_cost_to_borrow_request_preserves_historical_ticker_resolution():
    transport = CaptureTransport()
    client = OrtexBorrowClient(
        OrtexBorrowClientConfig(api_key="TEST", demo_mode=True),
        transport=transport,
    )
    client.cost_to_borrow(
        exchange_symbol="nyse",
        ticker="ABC",
        from_date=date(2020, 1, 1),
        to_date=date(2020, 1, 31),
        ticker_as_of_date=date(2020, 1, 1),
    )
    parsed = urlparse(transport.urls[0])
    query = parse_qs(parsed.query)
    assert parsed.path.endswith("/stock/nyse/ABC/ctb/all")
    assert query["ticker_as_of_date"] == ["2020-01-01"]
    assert transport.headers[0]["Ortex-Api-Key"] == "TEST"


def test_bulk_availability_request_is_date_specific():
    transport = CaptureTransport()
    client = OrtexBorrowClient(
        OrtexBorrowClientConfig(api_key="TEST", demo_mode=True),
        transport=transport,
    )
    client.short_availability_for_index(index_name="US-S 500", as_of_date=date(2026, 8, 3))
    query = parse_qs(urlparse(transport.urls[0]).query)
    assert query["date"] == ["2026-08-03"]
    assert query["index"] == ["US-S 500"]

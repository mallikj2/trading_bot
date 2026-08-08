from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID
import json

import pytest

from trading_bot.data.adapters.kibot import (
    KibotClient,
    KibotLicenseError,
    KibotSchemaError,
    exact_trade_vwap,
    normalize_daily_history,
    parse_adjustments,
    parse_daily_history,
    parse_minute_history,
    parse_tick_history,
)
from trading_bot.data.adapters.storage import RawSnapshotStore

UTC = timezone.utc
IID = UUID("11111111-1111-1111-1111-111111111111")


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get_text(self, params):
        self.calls.append(dict(params))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def test_paid_client_requires_license_gate():
    with pytest.raises(KibotLicenseError):
        KibotClient("alice", "secret", transport=FakeTransport([]), license_approved=False)


def test_guest_evaluation_can_login_and_fetch_daily():
    tx = FakeTransport(["200 OK\nAuthorizations\n", "01/02/2025,10,11,9,10.5,1000\n"])
    client = KibotClient(transport=tx, allow_guest_evaluation=True, license_approved=False)
    body = client.history("MSFT", interval="daily", start=date(2025, 1, 2), end=date(2025, 1, 2))
    assert body.startswith("01/02/2025")
    assert tx.calls[0]["action"] == "login"
    assert tx.calls[1]["unadjusted"] == "1"
    assert "user" not in tx.calls[1]
    assert "password" not in tx.calls[1]


def test_parse_daily_and_normalize_conservatively():
    text = "01/02/2025,10,11,9,10.5,1000\n01/03/2025,10.5,12,10,11.5,1200\n"
    rows = parse_daily_history(text)
    assert rows[0][0] == date(2025, 1, 2)
    assert rows[1][4] == Decimal("11.5")

    def close_at(d):
        return datetime(d.year, d.month, d.day, 21, 0, tzinfo=UTC)

    bars = normalize_daily_history(text, instrument_id=IID, source_snapshot_id="snap-1", session_close_at=close_at)
    assert bars[0].close == Decimal("10.5")
    assert bars[0].available_at > bars[0].observed_at


def test_duplicate_daily_rejected():
    text = "01/02/2025,10,11,9,10.5,1000\n01/02/2025,10,11,9,10.5,1000\n"
    with pytest.raises(KibotSchemaError):
        parse_daily_history(text)


def test_minute_parser_preserves_et_bar_open_semantics():
    bars = parse_minute_history("07/03/2025,10:00:00,10,11,9,10.5,100\n", symbol="AAPL")
    assert bars[0].interval_start.hour == 14  # 10:00 EDT normalized to UTC
    assert bars[0].interval_start.tzinfo is not None


def test_tick_vwap_is_exact_size_weighted():
    text = (
        "07/03/2025,10:00:01,100.00,100\n"
        "07/03/2025,10:15:01,102.00,300\n"
        "07/03/2025,10:30:00,200.00,100\n"
    )
    trades = parse_tick_history(text, symbol="AAPL")
    assert exact_trade_vwap(trades, session_date=date(2025, 7, 3)) == Decimal("101.50")


def test_adjustments_are_parsed_but_not_overinterpreted():
    text = "Date\tSymbol\tCompany\tAction\tDescription\n08/31/2020\tAAPL\tApple Inc.\tSplit\t4 for 1\n08/07/2020\tAAPL\tApple Inc.\tDividend\t0.2050\n"
    rows = parse_adjustments(text)
    assert rows[0].action == "Split"
    assert rows[0].description == "4 for 1"
    assert rows[1].action == "Dividend"


def test_text_snapshot_redacts_kibot_credentials(tmp_path: Path):
    store = RawSnapshotStore(tmp_path)
    receipt = store.persist_text(
        provider="Kibot",
        dataset_name="daily_unadjusted",
        dataset_version="1",
        adapter_version="KIBOT-HISTORICAL-v0.2.0",
        schema_version="KIBOT-DAILY-v1",
        retrieved_at=datetime(2026, 8, 8, 13, 0, tzinfo=UTC),
        request_parameters={"symbol": "AAPL", "username": "alice@example.com", "password": "dont-store"},
        payload_text="01/02/2025,10,11,9,10.5,1000\n",
        record_count=1,
        license_classification="PRIVATE_PERSONAL_RESEARCH_RETAINABLE",
        coverage_start=date(2025, 1, 2),
        coverage_end=date(2025, 1, 2),
        snapshot_id="snap-kibot",
        filename="response.csv",
    )
    manifest = json.loads(Path(receipt.manifest_path).read_text())
    assert manifest["request_parameters"]["username"] == "REDACTED"
    assert manifest["request_parameters"]["password"] == "REDACTED"
    assert Path(receipt.payload_path).read_text().startswith("01/02/2025")

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.data.adapters.massive import MassiveClient, MassiveSchemaError, normalize_nbbo_quotes

UTC = timezone.utc
IID = UUID("00000000-0000-0000-0000-000000000001")


def ns(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)


def test_massive_quotes_query_uses_historical_range() -> None:
    class FakeTransport:
        def __init__(self):
            self.urls = []

        def get_json(self, url, *, headers, timeout):
            self.urls.append(url)
            return {"status": "OK", "results": []}

    transport = FakeTransport()
    client = MassiveClient(api_key="secret", transport=transport, requests_per_second=100000)
    assert client.quotes("AAPL", start_ns=100, end_ns=200) == ()
    assert "timestamp.gte=100" in transport.urls[0]
    assert "timestamp.lt=200" in transport.urls[0]
    assert "apiKey=secret" in transport.urls[0]


def test_normalize_massive_quotes_skips_one_sided_states() -> None:
    participant = datetime(2026, 1, 5, 15, 0, tzinfo=UTC)
    rows = [
        {
            "bid_price": 100,
            "ask_price": 0,
            "bid_size": 10,
            "ask_size": 0,
            "participant_timestamp": ns(participant),
            "sip_timestamp": ns(participant) + 1_000_000,
            "sequence_number": 1,
        },
        {
            "bid_price": 100,
            "ask_price": 100.1,
            "bid_size": 10,
            "ask_size": 12,
            "participant_timestamp": ns(participant) + 2_000_000,
            "sip_timestamp": ns(participant) + 3_000_000,
            "sequence_number": 2,
        },
    ]
    result = normalize_nbbo_quotes(rows, instrument_id=IID, symbol="AAPL", source_snapshot_id="s")
    assert len(result) == 1
    assert result[0].bid_price == Decimal("100")
    assert result[0].ask_price == Decimal("100.1")


def test_normalize_massive_quotes_rejects_duplicate_sequence() -> None:
    participant = datetime(2026, 1, 5, 15, 0, tzinfo=UTC)
    row = {
        "bid_price": 100,
        "ask_price": 100.1,
        "bid_size": 10,
        "ask_size": 12,
        "participant_timestamp": ns(participant),
        "sip_timestamp": ns(participant) + 1_000_000,
        "sequence_number": 7,
    }
    with pytest.raises(MassiveSchemaError):
        normalize_nbbo_quotes([row, row], instrument_id=IID, symbol="AAPL", source_snapshot_id="s")


def test_normalize_massive_quotes_rejects_impossible_sip_order() -> None:
    participant = datetime(2026, 1, 5, 15, 0, tzinfo=UTC)
    row = {
        "bid_price": 100,
        "ask_price": 100.1,
        "bid_size": 10,
        "ask_size": 12,
        "participant_timestamp": ns(participant),
        "sip_timestamp": ns(participant) - 1_000_000,
        "sequence_number": 7,
    }
    with pytest.raises(MassiveSchemaError):
        normalize_nbbo_quotes([row], instrument_id=IID, symbol="AAPL", source_snapshot_id="s")

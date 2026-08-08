from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from trading_bot.data.adapters.databento_companion import (
    DatabentoCompanionError,
    exact_trade_vwap,
    find_ticker_reuse,
    normalize_security_master,
    normalize_trades,
    select_primary_listing_as_of,
)
from trading_bot.data.contracts import ListingState, SecurityType
from trading_bot.data.errors import PointInTimeError

UTC = timezone.utc


def _sm_row(**overrides):
    row = {
        "ts_effective": "2024-01-01T00:00:00Z",
        "ts_record": "2024-01-02T12:00:00Z",
        "listing_id": "L-1",
        "security_id": "S-1",
        "issuer_id": "I-1",
        "listing_status": "L",
        "listing_source": "M",
        "listing_date": "2000-01-01",
        "delisting_date": None,
        "security_type": "EQS",
        "primary_exchange": "USNASD",
        "symbol": "AAA",
        "nasdaq_symbol": "AAA",
        "figi": "BBG000AAA111",
        "us_code": "000000001",
        "cik": "1234",
        "shares_outstanding": "100000000",
        "shares_outstanding_date": "2023-12-31",
    }
    row.update(overrides)
    return row


def test_security_master_normalization_maps_pit_fields():
    rows = normalize_security_master([_sm_row()], source_snapshot_id="snap")
    row = rows[0]
    assert row.exchange == "NASDAQ"
    assert row.security_type == SecurityType.COMMON_STOCK
    assert row.listing_state == ListingState.LISTED
    assert row.cik == "0000001234"
    assert row.shares_outstanding == Decimal("100000000")
    assert row.effective_at < row.available_at


def test_security_master_future_record_cannot_backfill_decision():
    rows = normalize_security_master([_sm_row(ts_record="2024-06-01T00:00:00Z")], source_snapshot_id="snap")
    with pytest.raises(PointInTimeError):
        select_primary_listing_as_of(
            rows,
            instrument_id=rows[0].instrument_id,
            decision_at=datetime(2024, 3, 1, tzinfo=UTC),
        )


def test_latest_known_security_master_record_wins():
    rows = normalize_security_master(
        [
            _sm_row(),
            _sm_row(
                ts_effective="2024-04-01T00:00:00Z",
                ts_record="2024-04-01T01:00:00Z",
                symbol="BBB",
                nasdaq_symbol="BBB",
            ),
        ],
        source_snapshot_id="snap",
    )
    selected = select_primary_listing_as_of(
        rows,
        instrument_id=rows[0].instrument_id,
        decision_at=datetime(2024, 5, 1, tzinfo=UTC),
    )
    assert selected.nasdaq_symbol == "BBB"


def test_ticker_reuse_detects_different_security_ids():
    rows = normalize_security_master(
        [
            _sm_row(security_id="S-1", listing_id="L-1", issuer_id="I-1", symbol="REUSE", nasdaq_symbol="REUSE"),
            _sm_row(
                security_id="S-2",
                listing_id="L-2",
                issuer_id="I-2",
                symbol="REUSE",
                nasdaq_symbol="REUSE",
                ts_effective="2025-01-01T00:00:00Z",
                ts_record="2025-01-01T01:00:00Z",
            ),
        ],
        source_snapshot_id="snap",
    )
    reuse = find_ticker_reuse(rows)
    assert reuse["REUSE"] == ("S-1", "S-2")


def _trade(ts_event, price, size, **overrides):
    row = {
        "ts_event": ts_event,
        "ts_recv": ts_event,
        "instrument_id": 42,
        "publisher_id": 7,
        "action": "T",
        "price": price,
        "size": size,
        "flags": 0,
    }
    row.update(overrides)
    return row


def test_exact_trade_vwap_uses_dst_correct_et_window():
    rows = normalize_trades(
        [
            _trade("2025-07-03T13:59:59Z", 90, 10),  # 09:59:59 EDT excluded
            _trade("2025-07-03T14:00:01Z", 100, 100),
            _trade("2025-07-03T14:15:00Z", 102, 300),
            _trade("2025-07-03T14:30:00Z", 200, 10),  # exact end excluded
        ]
    )
    result = exact_trade_vwap(rows, session_date=date(2025, 7, 3))
    assert result.vwap == Decimal("101.5")
    assert result.trade_count == 2
    assert result.total_volume == 400


def test_exact_trade_vwap_rejects_quality_gap_flag():
    rows = normalize_trades([_trade("2025-07-03T14:05:00Z", 100, 100, flags=4)])
    with pytest.raises(DatabentoCompanionError):
        exact_trade_vwap(rows, session_date=date(2025, 7, 3))


def test_exact_trade_vwap_rejects_multiple_provider_instrument_ids():
    rows = normalize_trades(
        [
            _trade("2025-07-03T14:05:00Z", 100, 100),
            _trade("2025-07-03T14:10:00Z", 101, 100, instrument_id=43),
        ]
    )
    with pytest.raises(DatabentoCompanionError):
        exact_trade_vwap(rows, session_date=date(2025, 7, 3))

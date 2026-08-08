from datetime import date, datetime, timezone
from decimal import Decimal

from trading_bot.data.adapters.databento_companion import (
    exact_trade_vwap,
    normalize_security_master,
    normalize_trades,
)
from trading_bot.data.adapters.sec_sector_crawl import parse_target_ledger
from trading_bot.data.contracts import DataQualityStatus, ListingState, SecurityType, UniverseInput
from trading_bot.data.pit_acceptance import build_sector_blind_target_ledger, ledger_payload

UTC = timezone.utc
HASH = "f" * 64


def test_databento_pit_identity_to_sec_target_ledger_and_exact_execution_vwap():
    listings = normalize_security_master(
        [
            {
                "ts_effective": "2024-01-01T00:00:00Z",
                "ts_record": "2024-01-01T00:05:00Z",
                "listing_id": "LISTING-AAPL",
                "security_id": "SECURITY-AAPL",
                "issuer_id": "ISSUER-AAPL",
                "listing_status": "L",
                "listing_source": "M",
                "listing_date": "1980-12-12",
                "security_type": "EQS",
                "primary_exchange": "USNASD",
                "symbol": "AAPL",
                "nasdaq_symbol": "AAPL",
                "figi": "BBG000B9Y5X2",
                "us_code": "037833100",
                "cik": "320193",
                "shares_outstanding": "15000000000",
                "shares_outstanding_date": "2025-01-30",
            }
        ],
        source_snapshot_id="pit-security-master-snapshot",
    )
    listing = listings[0]
    freeze_at = datetime(2025, 1, 31, 21, 30, tzinfo=UTC)
    universe_input = UniverseInput(
        instrument_id=listing.instrument_id,
        exchange="NASDAQ",
        security_type=SecurityType.COMMON_STOCK,
        listing_state=ListingState.LISTED,
        adjusted_close=Decimal("100"),
        market_cap=Decimal("3000000000"),
        adv60=Decimal("50000000"),
        valid_sessions=500,
        vol20_annualized=Decimal("0.30"),
        sector_code=None,
        quality_status=DataQualityStatus.VALID,
        unresolved_corporate_action=False,
        identity_resolved=True,
        latest_available_at=datetime(2025, 1, 31, 21, 0, tzinfo=UTC),
        source_manifest_hashes=(HASH,),
    )
    build = build_sector_blind_target_ledger(
        [universe_input],
        listing_observations=listings,
        effective_month=date(2025, 2, 1),
        freeze_at=freeze_at,
        source_manifest_hash=HASH,
        universe_version="csmom-ls-v0.2-sector-blind",
    )
    payload = ledger_payload([build])
    sec_requirements = parse_target_ledger(payload)
    assert len(sec_requirements) == 1
    assert sec_requirements[0].instrument_id == listing.instrument_id
    assert sec_requirements[0].cik == "0000320193"
    assert sec_requirements[0].decision_at == freeze_at

    # 2025-01-31 is EST, so 10:00 ET == 15:00 UTC.
    trades = normalize_trades(
        [
            {
                "ts_event": "2025-01-31T15:00:01Z",
                "ts_recv": "2025-01-31T15:00:01.001Z",
                "instrument_id": 12345,
                "price": "100.00",
                "size": 100,
                "flags": 0,
                "sequence": 1,
                "publisher_id": 1,
            },
            {
                "ts_event": "2025-01-31T15:29:59Z",
                "ts_recv": "2025-01-31T15:29:59.001Z",
                "instrument_id": 12345,
                "price": "101.00",
                "size": 300,
                "flags": 0,
                "sequence": 2,
                "publisher_id": 1,
            },
        ]
    )
    vwap = exact_trade_vwap(trades, session_date=date(2025, 1, 31))
    assert vwap.trade_count == 2
    assert vwap.total_volume == 400
    assert vwap.vwap == Decimal("100.75")

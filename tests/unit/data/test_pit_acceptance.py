from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from trading_bot.data.adapters.databento_companion import normalize_security_master
from trading_bot.data.contracts import DataQualityStatus, ListingState, SecurityType, UniverseInput
from trading_bot.data.pit_acceptance import PitAcceptanceError, build_sector_blind_target_ledger, ledger_payload
from trading_bot.data.universe import build_monthly_universe

UTC = timezone.utc
HASH = "a" * 64


def _listing(cik="320193"):
    return normalize_security_master(
        [{
            "ts_effective": "2020-01-01T00:00:00Z",
            "ts_record": "2020-01-01T01:00:00Z",
            "listing_id": "L-1",
            "security_id": "S-1",
            "issuer_id": "I-1",
            "listing_status": "L",
            "listing_source": "M",
            "listing_date": "1980-12-12",
            "delisting_date": None,
            "security_type": "EQS",
            "primary_exchange": "USNASD",
            "symbol": "AAPL",
            "nasdaq_symbol": "AAPL",
            "figi": "BBG000B9Y5X2",
            "us_code": "037833100",
            "cik": cik,
            "shares_outstanding": "15000000000",
            "shares_outstanding_date": "2025-01-01",
        }],
        source_snapshot_id="sm-snap",
    )[0]


def _input(instrument_id):
    return UniverseInput(
        instrument_id=instrument_id,
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


def test_sector_blind_builder_keeps_row_that_final_universe_rejects_for_sector():
    listing = _listing()
    inp = _input(listing.instrument_id)
    final = build_monthly_universe(
        [inp],
        effective_month=date(2025, 2, 1),
        freeze_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
        source_manifest_hash=HASH,
        universe_version="u1",
    )
    assert final[0].eligible is False

    build = build_sector_blind_target_ledger(
        [inp],
        listing_observations=[listing],
        effective_month=date(2025, 2, 1),
        freeze_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
        source_manifest_hash=HASH,
        universe_version="u1",
    )
    assert build.eligible_count == 1
    payload = ledger_payload([build])
    assert payload["sector_blind"] is True
    assert payload["rows"][0]["cik"] == "0000320193"


def test_sector_blind_builder_fails_if_otherwise_eligible_identity_lacks_cik():
    listing = _listing(cik="")
    inp = _input(listing.instrument_id)
    with pytest.raises(PitAcceptanceError):
        build_sector_blind_target_ledger(
            [inp],
            listing_observations=[listing],
            effective_month=date(2025, 2, 1),
            freeze_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
            source_manifest_hash=HASH,
            universe_version="u1",
        )


def test_sector_blind_builder_cross_checks_exchange():
    listing = _listing()
    inp = _input(listing.instrument_id)
    wrong = UniverseInput(
        instrument_id=inp.instrument_id,
        exchange="NYSE",
        security_type=inp.security_type,
        listing_state=inp.listing_state,
        adjusted_close=inp.adjusted_close,
        market_cap=inp.market_cap,
        adv60=inp.adv60,
        valid_sessions=inp.valid_sessions,
        vol20_annualized=inp.vol20_annualized,
        sector_code=None,
        quality_status=inp.quality_status,
        unresolved_corporate_action=inp.unresolved_corporate_action,
        identity_resolved=inp.identity_resolved,
        latest_available_at=inp.latest_available_at,
        source_manifest_hashes=inp.source_manifest_hashes,
    )
    with pytest.raises(PitAcceptanceError):
        build_sector_blind_target_ledger(
            [wrong],
            listing_observations=[listing],
            effective_month=date(2025, 2, 1),
            freeze_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
            source_manifest_hash=HASH,
            universe_version="u1",
        )


def test_market_cap_from_pit_listing_is_point_in_time():
    from trading_bot.data.contracts import DailyBar
    from trading_bot.data.pit_acceptance import derive_market_cap_from_pit_listing

    listing = _listing()
    bar = DailyBar(
        instrument_id=listing.instrument_id,
        session_date=date(2025, 1, 31),
        open=Decimal("99"), high=Decimal("101"), low=Decimal("98"), close=Decimal("100"), volume=1_000_000,
        observed_at=datetime(2025, 1, 31, 21, 0, tzinfo=UTC),
        available_at=datetime(2025, 1, 31, 21, 20, tzinfo=UTC),
        snapshot_id="bar-snap",
    )
    cap = derive_market_cap_from_pit_listing(
        listing=listing,
        raw_close_bar=bar,
        decision_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
        source_snapshot_id="cap-snap",
    )
    assert cap.market_cap == Decimal("1500000000000")

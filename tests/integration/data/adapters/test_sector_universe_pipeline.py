from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from trading_bot.data.adapters.sec_filing_sic import (
    build_sector_history,
    parse_filing_sic,
    select_sector_as_of,
)
from trading_bot.data.contracts import (
    DataQualityStatus,
    ListingState,
    SecurityType,
    UniverseInput,
)
from trading_bot.data.universe import build_monthly_universe

UTC = timezone.utc


def _filing(accession: str, acceptance: str, sic: str, description: str) -> str:
    return f"""<SEC-DOCUMENT>{accession}.txt
<SEC-HEADER>{accession}.hdr.sgml
<ACCEPTANCE-DATETIME>{acceptance}
ACCESSION NUMBER:               {accession}
CONFORMED SUBMISSION TYPE:      10-Q
FILER:
    COMPANY DATA:
        COMPANY CONFORMED NAME:          TEST COMPANY
        CENTRAL INDEX KEY:               0000320193
        STANDARD INDUSTRIAL CLASSIFICATION: {description} [{sic}]
    FILING VALUES:
        FORM TYPE:                       10-Q
<DOCUMENT>
"""


def test_frozen_universe_uses_only_sector_known_at_month_end():
    instrument_id = uuid4()
    first = parse_filing_sic(
        _filing("0000320193-25-000001", "20250201161530", "3571", "ELECTRONIC COMPUTERS"),
        instrument_id=instrument_id,
        target_cik="320193",
        source_snapshot_id="sector-snap-1",
    )
    later = parse_filing_sic(
        _filing("0000320193-25-000002", "20250801162000", "5734", "RETAIL-COMPUTER STORES"),
        instrument_id=instrument_id,
        target_cik="320193",
        source_snapshot_id="sector-snap-2",
    )
    history = build_sector_history([first, later])
    june_freeze = datetime(2025, 6, 30, 20, 30, tzinfo=UTC)
    sector = select_sector_as_of(history, decision_at=june_freeze)

    row = UniverseInput(
        instrument_id=instrument_id,
        exchange="NASDAQ",
        security_type=SecurityType.COMMON_STOCK,
        listing_state=ListingState.LISTED,
        adjusted_close=Decimal("100"),
        market_cap=Decimal("3000000000"),
        adv60=Decimal("50000000"),
        valid_sessions=500,
        vol20_annualized=Decimal("0.25"),
        sector_code=sector.sector_code,
        quality_status=DataQualityStatus.VALID,
        unresolved_corporate_action=False,
        identity_resolved=True,
        latest_available_at=max(sector.available_at, datetime(2025, 6, 30, 20, 15, tzinfo=UTC)),
        source_manifest_hashes=("a" * 64,),
    )
    membership = build_monthly_universe(
        [row],
        effective_month=date(2025, 7, 1),
        freeze_at=june_freeze,
        source_manifest_hash="b" * 64,
        universe_version="2025-07-v1",
    )[0]

    assert membership.eligible is True
    assert sector.sector_code == "06_BUSEQ"

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import tempfile
import unittest
from uuid import uuid4
from zoneinfo import ZoneInfo

from trading_bot.data.adapters.massive import normalize_daily_bars, normalize_ticker_references
from trading_bot.data.adapters.sec_edgar import (
    build_accession_acceptance_map,
    derive_market_cap,
    extract_shares_outstanding,
    select_shares_as_of,
)
from trading_bot.data.adapters.storage import RawSnapshotStore
from trading_bot.data.leakage import assert_no_future_information

UTC = timezone.utc
NY = ZoneInfo("America/New_York")


class AdapterKernelPipelineTests(unittest.TestCase):
    def test_raw_to_normalized_to_pit_market_cap(self):
        instrument_id = uuid4()
        retrieved = datetime(2026, 8, 6, tzinfo=UTC)
        ticker_payload = {
            "status": "OK",
            "results": [
                {
                    "ticker": "TEST",
                    "name": "Test Corp",
                    "primary_exchange": "XNYS",
                    "type": "CS",
                    "active": True,
                    "cik": "123456",
                    "share_class_figi": "BBGTEST00001",
                    "last_updated_utc": "2025-01-31T21:00:00Z",
                }
            ],
        }
        submissions = {
            "cik": "123456",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000123456-25-000001"],
                    "acceptanceDateTime": ["2025-02-01T16:00:00-05:00"],
                    "filingDate": ["2025-02-01"],
                    "form": ["10-Q"],
                }
            },
        }
        facts = {
            "facts": {
                "dei": {
                    "EntityCommonStockSharesOutstanding": {
                        "units": {
                            "shares": [
                                {
                                    "end": "2025-01-25",
                                    "val": 30_000_000,
                                    "accn": "0000123456-25-000001",
                                    "form": "10-Q",
                                    "filed": "2025-02-01",
                                }
                            ]
                        }
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = RawSnapshotStore(tmp)
            ticker_receipt = store.persist_json(
                provider="MASSIVE",
                dataset_name="tickers",
                dataset_version="2025-01-31",
                adapter_version="v0.2.0",
                schema_version="1",
                retrieved_at=retrieved,
                request_parameters={"date": "2025-01-31", "apiKey": "secret"},
                payload=ticker_payload,
                record_count=1,
                license_classification="LICENSE_REVIEW_PENDING",
            )
            sec_receipt = store.persist_json(
                provider="SEC",
                dataset_name="companyfacts",
                dataset_version="2025-02-01",
                adapter_version="v0.2.0",
                schema_version="1",
                retrieved_at=retrieved,
                request_parameters={"cik": "0000123456"},
                payload=facts,
                record_count=1,
                license_classification="PUBLIC_DOMAIN_GOVERNMENT_DATA",
            )

            references = normalize_ticker_references(
                ticker_payload["results"],
                as_of_date=date(2025, 1, 31),
                as_of_available_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
                source_snapshot_id=ticker_receipt.snapshot_id,
                validated_historical_as_of_semantics=True,
            )
            self.assertEqual(references[0].cik, "0000123456")

            daily = normalize_daily_bars(
                [{"t": int(datetime(2025, 2, 3, 0, 0, tzinfo=NY).timestamp() * 1000), "o": 99, "h": 101, "l": 98, "c": 100, "v": 1000}],
                instrument_id=instrument_id,
                source_snapshot_id="bars-snap",
                session_close_at=lambda _: datetime(2025, 2, 3, 16, 0, tzinfo=NY),
            )[0]
            shares_rows = extract_shares_outstanding(
                facts,
                instrument_id=instrument_id,
                accession_acceptance=build_accession_acceptance_map(submissions),
                source_snapshot_id=sec_receipt.snapshot_id,
            )
            shares = select_shares_as_of(shares_rows, decision_at=datetime(2025, 2, 4, tzinfo=UTC))
            market_cap = derive_market_cap(
                instrument_id=instrument_id,
                raw_close_bar=daily,
                shares=shares,
                decision_at=datetime(2025, 2, 4, tzinfo=UTC),
                source_snapshot_id="market-cap-derived",
            )
            assert_no_future_information([daily, shares, market_cap], decision_at=datetime(2025, 2, 4, tzinfo=UTC))
            self.assertEqual(market_cap.market_cap, Decimal("3000000000"))


if __name__ == "__main__":
    unittest.main()

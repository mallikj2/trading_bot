from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest
from uuid import uuid4

from trading_bot.data.adapters.sec_edgar import (
    SecEdgarClient,
    SecSchemaError,
    build_accession_acceptance_map,
    derive_market_cap,
    extract_current_sic_reference,
    extract_shares_outstanding,
    historical_sector_from_submissions,
    select_shares_as_of,
)
from trading_bot.data.contracts import DailyBar
from trading_bot.data.errors import PointInTimeError

UTC = timezone.utc


def submissions_payload():
    return {
        "cik": "320193",
        "sic": "3571",
        "sicDescription": "Electronic Computers",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-25-000001", "0000320193-25-000002"],
                "acceptanceDateTime": ["2025-02-01T16:15:30-05:00", "2025-05-01T16:20:00-04:00"],
                "filingDate": ["2025-02-01", "2025-05-01"],
                "form": ["10-Q", "10-Q"],
            }
        },
    }


def companyfacts_payload(second_value=16_000_000_000):
    return {
        "cik": 320193,
        "facts": {
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {
                                "end": "2025-01-25",
                                "val": 15_000_000_000,
                                "accn": "0000320193-25-000001",
                                "fy": 2025,
                                "fp": "Q1",
                                "form": "10-Q",
                                "filed": "2025-02-01",
                            },
                            {
                                "end": "2025-04-26",
                                "val": second_value,
                                "accn": "0000320193-25-000002",
                                "fy": 2025,
                                "fp": "Q2",
                                "form": "10-Q",
                                "filed": "2025-05-01",
                            },
                        ]
                    }
                }
            }
        },
    }


class SecAdapterTests(unittest.TestCase):
    def test_client_requires_real_contact_user_agent(self):
        with self.assertRaises(ValueError):
            SecEdgarClient(user_agent="quant-bot")
        with self.assertRaises(ValueError):
            SecEdgarClient(user_agent="quant-bot owner@example.com", requests_per_second=11)

    def test_acceptance_map_uses_timestamp_not_filing_date(self):
        values = build_accession_acceptance_map(submissions_payload())
        self.assertEqual(values["0000320193-25-000001"], datetime(2025, 2, 1, 21, 15, 30, tzinfo=UTC))

    def test_extract_and_select_shares_point_in_time(self):
        instrument_id = uuid4()
        acceptance = build_accession_acceptance_map(submissions_payload())
        rows = extract_shares_outstanding(
            companyfacts_payload(),
            instrument_id=instrument_id,
            accession_acceptance=acceptance,
            source_snapshot_id="facts-snap",
        )
        early = select_shares_as_of(rows, decision_at=datetime(2025, 3, 1, tzinfo=UTC))
        late = select_shares_as_of(rows, decision_at=datetime(2025, 6, 1, tzinfo=UTC))
        self.assertEqual(early.shares_outstanding, Decimal("15000000000"))
        self.assertEqual(late.shares_outstanding, Decimal("16000000000"))

    def test_future_shares_revision_is_not_visible(self):
        instrument_id = uuid4()
        acceptance = build_accession_acceptance_map(submissions_payload())
        rows = extract_shares_outstanding(
            companyfacts_payload(),
            instrument_id=instrument_id,
            accession_acceptance=acceptance,
            source_snapshot_id="facts-snap",
        )
        selected = select_shares_as_of(rows, decision_at=datetime(2025, 4, 1, tzinfo=UTC))
        self.assertEqual(selected.accession_number, "0000320193-25-000001")

    def test_ambiguous_multiclass_facts_fail_closed(self):
        payload = companyfacts_payload()
        payload["facts"]["us-gaap"] = {
            "CommonStockSharesOutstanding": {
                "units": {
                    "shares": [
                        {
                            "end": "2025-01-25",
                            "val": 10,
                            "accn": "0000320193-25-000001",
                            "form": "10-Q",
                            "filed": "2025-02-01",
                        }
                    ]
                }
            }
        }
        with self.assertRaises(SecSchemaError):
            extract_shares_outstanding(
                payload,
                instrument_id=uuid4(),
                accession_acceptance=build_accession_acceptance_map(submissions_payload()),
                source_snapshot_id="snap",
            )

    def test_current_sic_is_explicitly_not_historical(self):
        reference = extract_current_sic_reference(
            submissions_payload(),
            retrieved_at=datetime(2026, 8, 6, tzinfo=UTC),
            source_snapshot_id="sub-snap",
        )
        self.assertFalse(reference.historical_use_allowed)
        with self.assertRaises(PointInTimeError):
            historical_sector_from_submissions(reference)

    def test_market_cap_derivation_requires_both_inputs_known(self):
        instrument_id = uuid4()
        acceptance = build_accession_acceptance_map(submissions_payload())
        shares = extract_shares_outstanding(
            companyfacts_payload(),
            instrument_id=instrument_id,
            accession_acceptance=acceptance,
            source_snapshot_id="facts-snap",
        )[0]
        bar = DailyBar(
            instrument_id=instrument_id,
            session_date=date(2025, 2, 3),
            open=Decimal("99"),
            high=Decimal("102"),
            low=Decimal("98"),
            close=Decimal("100"),
            volume=1000,
            observed_at=datetime(2025, 2, 3, 21, 0, tzinfo=UTC),
            available_at=datetime(2025, 2, 3, 21, 30, tzinfo=UTC),
            snapshot_id="bar-snap",
        )
        result = derive_market_cap(
            instrument_id=instrument_id,
            raw_close_bar=bar,
            shares=shares,
            decision_at=datetime(2025, 2, 4, tzinfo=UTC),
            source_snapshot_id="derived-snap",
        )
        self.assertEqual(result.market_cap, Decimal("1500000000000"))
        with self.assertRaises(PointInTimeError):
            derive_market_cap(
                instrument_id=instrument_id,
                raw_close_bar=bar,
                shares=shares,
                decision_at=datetime(2025, 2, 3, 21, 20, tzinfo=UTC),
                source_snapshot_id="derived-snap",
            )


if __name__ == "__main__":
    unittest.main()

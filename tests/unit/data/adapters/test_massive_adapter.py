from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest
from urllib.parse import parse_qs, urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

from trading_bot.data.adapters.massive import (
    MassiveClient,
    normalize_daily_bars,
    normalize_dividends,
    normalize_intraday_bars,
    normalize_overview_market_cap,
    normalize_overview_sector,
    normalize_splits,
    normalize_ticker_events,
    normalize_ticker_references,
)
from trading_bot.data.adapters.vwap import build_execution_vwap
from trading_bot.data.errors import DataContractError, PointInTimeError

UTC = timezone.utc
NY = ZoneInfo("America/New_York")


class FakeTransport:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.urls = []

    def get_json(self, url, *, headers, timeout):
        self.urls.append(url)
        return self.payloads.pop(0)


def epoch_ms(local_dt: datetime) -> int:
    return int(local_dt.astimezone(UTC).timestamp() * 1000)


class MassiveAdapterTests(unittest.TestCase):
    def test_pagination_preserves_api_key_without_duplicate(self):
        transport = FakeTransport(
            [
                {
                    "status": "OK",
                    "results": [{"ticker": "A"}],
                    "next_url": "https://api.massive.com/v3/reference/tickers?cursor=abc",
                },
                {"status": "OK", "results": [{"ticker": "B"}]},
            ]
        )
        client = MassiveClient(api_key="secret", transport=transport, requests_per_second=100000)
        rows = tuple(client.iter_results("/v3/reference/tickers", params={"limit": 1}))
        self.assertEqual([row["ticker"] for row in rows], ["A", "B"])
        for url in transport.urls:
            values = parse_qs(urlparse(url).query)
            self.assertEqual(values["apiKey"], ["secret"])

    def test_normalize_ticker_reference(self):
        rows = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "primary_exchange": "XNAS",
                "type": "CS",
                "active": True,
                "cik": "320193",
                "share_class_figi": "BBG001S5N8V8",
                "last_updated_utc": "2025-01-31T21:00:00Z",
            }
        ]
        result = normalize_ticker_references(
            rows,
            as_of_date=date(2025, 1, 31),
            as_of_available_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
            source_snapshot_id="snap",
            validated_historical_as_of_semantics=True,
        )
        self.assertEqual(result[0].cik, "0000320193")
        self.assertEqual(result[0].primary_exchange_mic, "XNAS")

    def test_ticker_snapshot_blocked_without_credentialed_semantics(self):
        with self.assertRaises(PointInTimeError):
            normalize_ticker_references(
                [{
                    "ticker": "AAPL", "name": "Apple", "primary_exchange": "XNAS",
                    "type": "CS", "active": True, "cik": "320193"
                }],
                as_of_date=date(2025, 1, 31),
                as_of_available_at=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
                source_snapshot_id="snap",
            )

    def test_ticker_events_create_half_open_aliases(self):
        aliases = normalize_ticker_events(
            {
                "results": {
                    "events": [
                        {"date": "2012-05-18", "type": "ticker_change", "ticker_change": {"ticker": "FB"}},
                        {"date": "2022-06-09", "type": "ticker_change", "ticker_change": {"ticker": "META"}},
                    ]
                }
            },
            instrument_id=uuid4(),
            exchange="NASDAQ",
            source_snapshot_id="events-snap",
            effective_at_for_date=lambda d: datetime.combine(d, datetime.min.time(), tzinfo=NY).replace(hour=9, minute=30),
        )
        self.assertEqual([item.symbol for item in aliases], ["FB", "META"])
        self.assertEqual(aliases[0].valid_to, aliases[1].valid_from)
        self.assertIsNone(aliases[1].valid_to)

    def test_overview_sector_requires_validation_and_maps_sic_division(self):
        payload = {"results": {"sic_code": "3571"}}
        with self.assertRaises(PointInTimeError):
            normalize_overview_sector(
                payload,
                instrument_id=uuid4(),
                effective_from=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
                source_snapshot_id="snap",
            )
        result = normalize_overview_sector(
            payload,
            instrument_id=uuid4(),
            effective_from=datetime(2025, 1, 31, 21, 30, tzinfo=UTC),
            source_snapshot_id="snap",
            validated_historical_as_of_semantics=True,
        )
        self.assertEqual(result.sector_code, "D")

    def test_daily_bar_uses_official_close_and_conservative_finality(self):
        instrument_id = uuid4()
        row = {
            "t": epoch_ms(datetime(2025, 1, 2, 0, 0, tzinfo=NY)),
            "o": 100,
            "h": 105,
            "l": 99,
            "c": 104,
            "v": 1000,
        }
        close = datetime(2025, 1, 2, 16, 0, tzinfo=NY)
        bars = normalize_daily_bars(
            [row],
            instrument_id=instrument_id,
            source_snapshot_id="snap",
            session_close_at=lambda _: close,
        )
        self.assertEqual(bars[0].observed_at, close.astimezone(UTC))
        self.assertEqual(bars[0].available_at, (close + timedelta(minutes=30)).astimezone(UTC))
        self.assertEqual(bars[0].close, Decimal("104"))

    def _intraday_rows(self, missing_index=None):
        rows = []
        for index, minute in enumerate(range(0, 30, 5)):
            if index == missing_index:
                continue
            rows.append(
                {
                    "t": epoch_ms(datetime(2025, 1, 3, 10, minute, tzinfo=NY)),
                    "o": 100 + index,
                    "h": 101 + index,
                    "l": 99 + index,
                    "c": 100.5 + index,
                    "v": 100 * (index + 1),
                    "vw": 100.25 + index,
                }
            )
        return rows

    def test_complete_intraday_window_builds_vwap(self):
        bars = normalize_intraday_bars(
            self._intraday_rows(),
            instrument_id=uuid4(),
            symbol="AAPL",
            source_snapshot_id="snap",
            interval_minutes=5,
            availability_lag=timedelta(0),
        )
        decision = datetime(2025, 1, 3, 10, 30, 1, tzinfo=NY)
        vwap = build_execution_vwap(
            bars,
            session_date=date(2025, 1, 3),
            decision_at=decision,
        )
        self.assertEqual(vwap.interval_count, 6)
        self.assertGreater(vwap.vwap, Decimal("100"))

    def test_incomplete_intraday_window_fails(self):
        bars = normalize_intraday_bars(
            self._intraday_rows(missing_index=2),
            instrument_id=uuid4(),
            symbol="AAPL",
            source_snapshot_id="snap",
            interval_minutes=5,
            availability_lag=timedelta(0),
        )
        with self.assertRaises(DataContractError):
            build_execution_vwap(
                bars,
                session_date=date(2025, 1, 3),
                decision_at=datetime(2025, 1, 3, 10, 31, tzinfo=NY),
            )

    def test_vwap_rejects_future_interval_availability(self):
        bars = normalize_intraday_bars(
            self._intraday_rows(),
            instrument_id=uuid4(),
            symbol="AAPL",
            source_snapshot_id="snap",
            interval_minutes=5,
            availability_lag=timedelta(seconds=10),
        )
        with self.assertRaises(PointInTimeError):
            build_execution_vwap(
                bars,
                session_date=date(2025, 1, 3),
                decision_at=datetime(2025, 1, 3, 10, 30, 5, tzinfo=NY),
            )

    def test_split_and_dividend_normalization_are_conservative(self):
        instrument_id = uuid4()
        at_open = lambda d: datetime.combine(d, datetime.min.time(), tzinfo=NY).replace(hour=9, minute=30)
        split = normalize_splits(
            [{"id": "s1", "execution_date": "2025-02-03", "split_from": 1, "split_to": 2}],
            instrument_id=instrument_id,
            source_snapshot_id="split-snap",
            effective_at_for_date=at_open,
        )[0]
        dividend = normalize_dividends(
            [{"id": "d1", "ex_dividend_date": "2025-02-10", "cash_amount": 0.25, "currency": "USD"}],
            instrument_id=instrument_id,
            source_snapshot_id="div-snap",
            effective_at_for_date=at_open,
        )[0]
        self.assertEqual(split.available_at, split.effective_at)
        self.assertEqual(dividend.available_at, dividend.effective_at)
        self.assertEqual(dividend.cash_amount, Decimal("0.25"))

    def test_provider_direct_market_cap_is_blocked_without_evidence(self):
        with self.assertRaises(PointInTimeError):
            normalize_overview_market_cap(
                {"results": {"market_cap": 2_500_000_000}},
                instrument_id=uuid4(),
                observed_at=datetime(2025, 1, 31, 21, 0, tzinfo=UTC),
                source_snapshot_id="snap",
            )


if __name__ == "__main__":
    unittest.main()

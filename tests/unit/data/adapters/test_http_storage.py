from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import unittest

from trading_bot.data.adapters.http import ProviderRequestError, SafeJsonClient, redact_url
from trading_bot.data.adapters.storage import RawSnapshotStore
from trading_bot.data.errors import ImmutableStorageError

UTC = timezone.utc


class FakeTransport:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.urls = []

    def get_json(self, url, *, headers, timeout):
        self.urls.append(url)
        if not self.payloads:
            raise AssertionError("unexpected request")
        value = self.payloads.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class HttpStorageTests(unittest.TestCase):
    def test_redact_url(self):
        rendered = redact_url("https://api.massive.com/v3/reference/tickers?apiKey=secret&limit=10")
        self.assertIn("apiKey=REDACTED", rendered)
        self.assertNotIn("secret", rendered)

    def test_safe_client_rejects_foreign_pagination_host(self):
        client = SafeJsonClient(
            base_url="https://api.massive.com",
            default_headers={},
            transport=FakeTransport([]),
        )
        with self.assertRaises(ProviderRequestError):
            client.get_json("https://evil.example/path")

    def test_snapshot_store_redacts_secrets_and_is_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RawSnapshotStore(tmp)
            receipt = store.persist_json(
                provider="MASSIVE",
                dataset_name="ticker_snapshot",
                dataset_version="2025-01-31",
                adapter_version="v1",
                schema_version="1",
                retrieved_at=datetime(2026, 8, 6, tzinfo=UTC),
                request_parameters={"apiKey": "super-secret", "date": "2025-01-31"},
                payload={"status": "OK", "results": [{"ticker": "AAPL"}]},
                record_count=1,
                license_classification="LICENSE_REVIEW_PENDING",
                snapshot_id="fixed-snapshot",
            )
            manifest_text = Path(receipt.manifest_path).read_text(encoding="utf-8")
            self.assertIn("REDACTED", manifest_text)
            self.assertNotIn("super-secret", manifest_text)
            self.assertEqual(len(receipt.manifest_hash), 64)
            with self.assertRaises(ImmutableStorageError):
                store.persist_json(
                    provider="MASSIVE",
                    dataset_name="ticker_snapshot",
                    dataset_version="2025-01-31",
                    adapter_version="v1",
                    schema_version="1",
                    retrieved_at=datetime(2026, 8, 6, tzinfo=UTC),
                    request_parameters={},
                    payload={"status": "OK"},
                    record_count=0,
                    license_classification="LICENSE_REVIEW_PENDING",
                    snapshot_id="fixed-snapshot",
                )


if __name__ == "__main__":
    unittest.main()

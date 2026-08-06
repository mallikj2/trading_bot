from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from trading_bot.data.contracts import (  # noqa: E402
    DataQualityStatus,
    ListingState,
    SecurityType,
    UniverseInput,
)
from trading_bot.data.manifests import DatasetManifest, build_source_file, verify_source_files  # noqa: E402
from trading_bot.data.universe import build_monthly_universe, universe_membership_hash  # noqa: E402

UTC = timezone.utc


class KernelReproducibilityTests(unittest.TestCase):
    def test_same_inputs_produce_same_manifest_and_universe_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw.jsonl"
            source.write_text('{"instrument_id":"00000000-0000-0000-0000-000000000001"}\n', encoding="utf-8")
            source_file = build_source_file(source, root)
            kwargs = dict(
                manifest_id="m1",
                dataset_name="universe-input",
                dataset_version="v1",
                provider="fixture",
                adapter_version="1",
                schema_version="1",
                retrieved_at=datetime(2024, 6, 28, 20, 25, tzinfo=UTC),
                coverage_start=date(2024, 6, 28),
                coverage_end=date(2024, 6, 28),
                request_parameters={},
                source_files=(source_file,),
                record_count=1,
                license_classification="TEST",
            )
            left_manifest = DatasetManifest(**kwargs)
            right_manifest = DatasetManifest(**kwargs)
            verify_source_files(left_manifest, root)
            self.assertEqual(left_manifest.content_hash, right_manifest.content_hash)

            row = UniverseInput(
                instrument_id=UUID("00000000-0000-0000-0000-000000000001"),
                exchange="NASDAQ",
                security_type=SecurityType.COMMON_STOCK,
                listing_state=ListingState.LISTED,
                adjusted_close=Decimal("50"),
                market_cap=Decimal("5000000000"),
                adv60=Decimal("50000000"),
                valid_sessions=500,
                vol20_annualized=Decimal("0.25"),
                sector_code="D",
                quality_status=DataQualityStatus.VALID,
                unresolved_corporate_action=False,
                identity_resolved=True,
                latest_available_at=datetime(2024, 6, 28, 20, 30, tzinfo=UTC),
                source_manifest_hashes=(left_manifest.content_hash,),
            )
            build_args = dict(
                effective_month=date(2024, 7, 1),
                freeze_at=datetime(2024, 6, 28, 20, 30, tzinfo=UTC),
                source_manifest_hash=left_manifest.content_hash,
                universe_version="2024-07-v1",
            )
            left = build_monthly_universe([row], **build_args)
            right = build_monthly_universe([row], **build_args)
            self.assertEqual(universe_membership_hash(left), universe_membership_hash(right))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from trading_bot.data.errors import ImmutableStorageError  # noqa: E402
from trading_bot.data.manifests import (  # noqa: E402
    DatasetManifest,
    build_source_file,
    verify_source_files,
    write_bytes_immutable,
    write_manifest_immutable,
)

UTC = timezone.utc


class ManifestTests(unittest.TestCase):
    def make_manifest(self, source_file):
        return DatasetManifest(
            manifest_id="manifest-1",
            dataset_name="daily-bars",
            dataset_version="2024-11-29.1",
            provider="fixture",
            adapter_version="1.0.0",
            schema_version="1",
            retrieved_at=datetime(2024, 11, 30, tzinfo=UTC),
            coverage_start=date(2024, 11, 29),
            coverage_end=date(2024, 11, 29),
            request_parameters={"adjusted": False},
            source_files=(source_file,),
            record_count=1,
            license_classification="TEST_FIXTURE",
        )

    def test_manifest_hash_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw.json"
            source.write_text('{"x":1}\n', encoding="utf-8")
            source_file = build_source_file(source, root)
            left = self.make_manifest(source_file)
            right = self.make_manifest(source_file)
            self.assertEqual(left.content_hash, right.content_hash)

    def test_source_verification_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw.json"
            source.write_text('{"x":1}\n', encoding="utf-8")
            manifest = self.make_manifest(build_source_file(source, root))
            source.write_text('{"x":2}\n', encoding="utf-8")
            with self.assertRaises(ImmutableStorageError):
                verify_source_files(manifest, root)

    def test_immutable_writer_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.bin"
            write_bytes_immutable(path, b"first")
            with self.assertRaises(ImmutableStorageError):
                write_bytes_immutable(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")

    def test_manifest_writer_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw.json"
            source.write_text('{"x":1}\n', encoding="utf-8")
            manifest = self.make_manifest(build_source_file(source, root))
            target = root / "manifest.json"
            write_manifest_immutable(target, manifest)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["dataset_name"], "daily-bars")

    def test_storage_manifest_id_does_not_change_lineage_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw.json"
            source.write_text('{"x":1}\n', encoding="utf-8")
            source_file = build_source_file(source, root)
            left = self.make_manifest(source_file)
            payload = dict(left.__dict__) if hasattr(left, "__dict__") else None
            right = DatasetManifest(
                manifest_id="different-storage-id",
                dataset_name=left.dataset_name,
                dataset_version=left.dataset_version,
                provider=left.provider,
                adapter_version=left.adapter_version,
                schema_version=left.schema_version,
                retrieved_at=left.retrieved_at,
                coverage_start=left.coverage_start,
                coverage_end=left.coverage_end,
                request_parameters=left.request_parameters,
                source_files=left.source_files,
                record_count=left.record_count,
                license_classification=left.license_classification,
            )
            self.assertIsNone(payload)
            self.assertEqual(left.content_hash, right.content_hash)


if __name__ == "__main__":
    unittest.main()

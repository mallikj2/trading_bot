"""Immutable provider snapshot persistence and manifest creation."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from ..hashing import canonical_json
from ..manifests import (
    DatasetManifest,
    build_source_file,
    write_bytes_immutable,
    write_manifest_immutable,
)
from ..time_utils import require_aware
from .models import SnapshotReceipt


_SECRET_KEYS = {"apikey", "api_key", "authorization", "token", "access_token", "secret"}


def redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): ("REDACTED" if str(key).lower() in _SECRET_KEYS else redact_secrets(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value


class RawSnapshotStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def persist_json(
        self,
        *,
        provider: str,
        dataset_name: str,
        dataset_version: str,
        adapter_version: str,
        schema_version: str,
        retrieved_at: datetime,
        request_parameters: Mapping[str, Any],
        payload: Mapping[str, Any],
        record_count: int,
        license_classification: str,
        coverage_start: date | None = None,
        coverage_end: date | None = None,
        parent_manifest_ids: tuple[str, ...] = (),
        snapshot_id: str | None = None,
    ) -> SnapshotReceipt:
        retrieved = require_aware(retrieved_at, "retrieved_at")
        if record_count < 0:
            raise ValueError("record_count cannot be negative")
        sid = snapshot_id or str(uuid4())
        snapshot_root = (
            self.root
            / provider.lower()
            / dataset_name
            / retrieved.date().isoformat()
            / sid
        )
        payload_path = snapshot_root / "response.json"
        payload_bytes = (canonical_json(payload) + "\n").encode("utf-8")
        write_bytes_immutable(payload_path, payload_bytes)
        source_file = build_source_file(payload_path, snapshot_root)
        manifest = DatasetManifest(
            manifest_id=str(uuid4()),
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            provider=provider,
            adapter_version=adapter_version,
            schema_version=schema_version,
            retrieved_at=retrieved,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            request_parameters=redact_secrets(request_parameters),
            source_files=(source_file,),
            record_count=record_count,
            license_classification=license_classification,
            parent_manifest_ids=parent_manifest_ids,
        )
        manifest_path = snapshot_root / "manifest.json"
        write_manifest_immutable(manifest_path, manifest)
        return SnapshotReceipt(
            snapshot_id=sid,
            snapshot_root=snapshot_root.as_posix(),
            payload_path=payload_path.as_posix(),
            manifest_path=manifest_path.as_posix(),
            manifest_hash=manifest.content_hash,
            record_count=record_count,
        )

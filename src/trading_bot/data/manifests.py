"""Immutable source snapshots and dataset manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping
import os
import tempfile

from .errors import ImmutableStorageError
from .hashing import canonical_json, content_hash, sha256_file
from .time_utils import require_aware


@dataclass(frozen=True, slots=True)
class SourceFile:
    relative_path: str
    sha256_hex: str
    size_bytes: int

    def __post_init__(self) -> None:
        candidate = Path(self.relative_path)
        if (
            not self.relative_path
            or candidate.is_absolute()
            or ".." in candidate.parts
        ):
            raise ValueError("relative_path must be non-empty, relative, and contained")
        if len(self.sha256_hex) != 64:
            raise ValueError("sha256_hex must contain 64 hex characters")
        int(self.sha256_hex, 16)
        if self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    manifest_id: str
    dataset_name: str
    dataset_version: str
    provider: str
    adapter_version: str
    schema_version: str
    retrieved_at: datetime
    coverage_start: date | None
    coverage_end: date | None
    request_parameters: Mapping[str, Any]
    source_files: tuple[SourceFile, ...]
    record_count: int
    license_classification: str
    parent_manifest_ids: tuple[str, ...] = ()
    build_status: str = "SUCCESS"
    quality_report_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "retrieved_at", require_aware(self.retrieved_at, "retrieved_at"))
        required = (
            self.manifest_id,
            self.dataset_name,
            self.dataset_version,
            self.provider,
            self.adapter_version,
            self.schema_version,
            self.license_classification,
        )
        if any(not value.strip() for value in required):
            raise ValueError("manifest identity fields cannot be blank")
        if self.record_count < 0:
            raise ValueError("record_count cannot be negative")
        if self.coverage_start and self.coverage_end and self.coverage_end < self.coverage_start:
            raise ValueError("coverage_end cannot precede coverage_start")
        if not self.source_files:
            raise ValueError("manifest requires at least one source file")

    @property
    def content_hash(self) -> str:
        # manifest_id is a storage identifier, not a research input. Excluding
        # it makes lineage reproducible across equivalent rebuilds.
        payload = asdict(self)
        payload.pop("manifest_id", None)
        return content_hash(payload)


def build_source_file(path: str | Path, snapshot_root: str | Path) -> SourceFile:
    file_path = Path(path).resolve()
    root = Path(snapshot_root).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    try:
        relative = file_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("source file must be inside snapshot_root") from exc
    return SourceFile(
        relative_path=relative.as_posix(),
        sha256_hex=sha256_file(file_path),
        size_bytes=file_path.stat().st_size,
    )


def verify_source_files(manifest: DatasetManifest, snapshot_root: str | Path) -> None:
    root = Path(snapshot_root).resolve()
    for source in manifest.source_files:
        path = (root / source.relative_path).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ImmutableStorageError(
                f"source file escapes snapshot root: {source.relative_path}"
            ) from exc
        if not path.is_file():
            raise ImmutableStorageError(f"missing source file: {source.relative_path}")
        if path.stat().st_size != source.size_bytes:
            raise ImmutableStorageError(f"size mismatch: {source.relative_path}")
        if sha256_file(path) != source.sha256_hex:
            raise ImmutableStorageError(f"hash mismatch: {source.relative_path}")


def write_bytes_immutable(path: str | Path, payload: bytes) -> None:
    """Atomically create a file and reject any overwrite, even identical bytes."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ImmutableStorageError(f"immutable path already exists: {target}")

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError as exc:
            raise ImmutableStorageError(f"immutable path already exists: {target}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def write_json_immutable(path: str | Path, value: Any) -> None:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    write_bytes_immutable(path, payload)


def write_manifest_immutable(path: str | Path, manifest: DatasetManifest) -> None:
    write_json_immutable(path, manifest)

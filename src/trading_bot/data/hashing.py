"""Canonical hashing utilities for reproducible datasets."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID
import json


def _canonicalize(value: Any) -> Any:
    if is_dataclass(value):
        return _canonicalize(asdict(value))
    if isinstance(value, dict):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_canonicalize(item) for item in value), key=repr)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Path):
        return value.as_posix()
    return value


def canonical_json(value: Any) -> str:
    """Serialize a Python value deterministically for hashing."""
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def sha256_file(path: str | Path, chunk_size: int = 1_048_576) -> str:
    file_path = Path(path)
    digest = sha256()
    with file_path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def content_hash(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))

"""Immutable domain-event envelope for Phase 02B PF03.

Events describe facts that already happened in the deterministic research/runtime
model.  They are content-addressed: the event ID is the SHA-256 of the canonical
immutable event body.  Journal storage metadata (sequence/recorded_at/hash-chain)
is deliberately separate so re-appending the same domain event is idempotent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from trading_bot.data.time_utils import require_aware


_EVENT_TYPE_RE = re.compile(r"^[A-Z][A-Z0-9_]*(?:\.[A-Z0-9_]+)*$")
_ZERO_HASH = "0" * 64


class EventContractError(ValueError):
    """Raised when an event violates the immutable event contract."""


JsonScalar = str | int | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def _normalize_json(value: Any, path: str = "payload") -> JsonValue:
    """Normalize a JSON payload while rejecting nondeterministic values.

    Floats are rejected intentionally. Monetary/ratio values should be encoded as
    decimal strings by the producing domain model so canonical hashes do not
    depend on binary floating-point formatting.
    """
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        raise EventContractError(f"{path} cannot contain float values; use decimal strings")
    if isinstance(value, Mapping):
        normalized: dict[str, JsonValue] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str) or not raw_key:
                raise EventContractError(f"{path} keys must be non-empty strings")
            normalized[raw_key] = _normalize_json(raw_value, f"{path}.{raw_key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item, f"{path}[]") for item in value]
    raise EventContractError(f"{path} contains unsupported value type {type(value).__name__}")


def canonical_json(value: Mapping[str, Any] | JsonValue) -> str:
    normalized = _normalize_json(value)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(raw: str) -> str:
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    occurred_at: datetime
    correlation_id: str
    causation_id: str | None
    producer: str
    schema_version: int
    payload_json: str

    def __post_init__(self) -> None:
        if not _EVENT_TYPE_RE.fullmatch(self.event_type):
            raise EventContractError(
                "event_type must be uppercase dot-delimited tokens, e.g. TRADE_LEAD.SNAPSHOT"
            )
        for field_name in ("aggregate_type", "aggregate_id", "correlation_id", "producer"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise EventContractError(f"{field_name} is required")
        if self.causation_id is not None and not self.causation_id.strip():
            raise EventContractError("causation_id cannot be blank")
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, int):
            raise EventContractError("schema_version must be an integer")
        if self.schema_version <= 0:
            raise EventContractError("schema_version must be positive")
        object.__setattr__(self, "occurred_at", require_aware(self.occurred_at, "occurred_at"))

        try:
            decoded = json.loads(self.payload_json)
        except json.JSONDecodeError as exc:
            raise EventContractError("payload_json must contain valid JSON") from exc
        if not isinstance(decoded, dict):
            raise EventContractError("event payload must be a JSON object")
        normalized_json = canonical_json(decoded)
        object.__setattr__(self, "payload_json", normalized_json)

        expected = self.compute_event_id()
        if self.event_id != expected:
            raise EventContractError("event_id does not match canonical event body")
        if self.causation_id == self.event_id:
            raise EventContractError("event cannot cause itself")

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        occurred_at: datetime,
        correlation_id: str,
        payload: Mapping[str, Any],
        causation_id: str | None = None,
        producer: str = "trading_bot",
        schema_version: int = 1,
    ) -> "DomainEvent":
        occurred = require_aware(occurred_at, "occurred_at")
        payload_json = canonical_json(payload)
        provisional = cls.__new__(cls)
        object.__setattr__(provisional, "event_id", _ZERO_HASH)
        object.__setattr__(provisional, "event_type", event_type)
        object.__setattr__(provisional, "aggregate_type", aggregate_type)
        object.__setattr__(provisional, "aggregate_id", aggregate_id)
        object.__setattr__(provisional, "occurred_at", occurred)
        object.__setattr__(provisional, "correlation_id", correlation_id)
        object.__setattr__(provisional, "causation_id", causation_id)
        object.__setattr__(provisional, "producer", producer)
        object.__setattr__(provisional, "schema_version", schema_version)
        object.__setattr__(provisional, "payload_json", payload_json)
        event_id = provisional.compute_event_id()
        return cls(
            event_id=event_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            occurred_at=occurred,
            correlation_id=correlation_id,
            causation_id=causation_id,
            producer=producer,
            schema_version=schema_version,
            payload_json=payload_json,
        )

    @property
    def payload(self) -> dict[str, JsonValue]:
        value = json.loads(self.payload_json)
        assert isinstance(value, dict)
        return value

    def body_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "producer": self.producer,
            "schema_version": self.schema_version,
            "payload": self.payload,
        }

    def compute_event_id(self) -> str:
        return sha256_hex(canonical_json(self.body_dict()))

    @property
    def content_hash(self) -> str:
        return self.compute_event_id()

    def to_dict(self) -> dict[str, Any]:
        return {"event_id": self.event_id, **self.body_dict()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DomainEvent":
        raw_payload = payload.get("payload")
        if not isinstance(raw_payload, Mapping):
            raise EventContractError("payload must be a JSON object")
        return cls(
            event_id=str(payload["event_id"]),
            event_type=str(payload["event_type"]),
            aggregate_type=str(payload["aggregate_type"]),
            aggregate_id=str(payload["aggregate_id"]),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            correlation_id=str(payload["correlation_id"]),
            causation_id=None if payload.get("causation_id") is None else str(payload["causation_id"]),
            producer=str(payload["producer"]),
            schema_version=int(payload["schema_version"]),
            payload_json=canonical_json(raw_payload),
        )

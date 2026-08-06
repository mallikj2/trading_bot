"""Fail-closed historical leakage checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol

from .errors import LeakageError
from .time_utils import require_aware


class AvailableRecord(Protocol):
    available_at: datetime


@dataclass(frozen=True, slots=True)
class LeakageFinding:
    code: str
    message: str
    record_repr: str


def scan_future_information(
    records: Iterable[AvailableRecord],
    *,
    decision_at: datetime,
) -> tuple[LeakageFinding, ...]:
    decision = require_aware(decision_at, "decision_at")
    findings: list[LeakageFinding] = []
    for record in records:
        available = require_aware(record.available_at, "record.available_at")
        if available > decision:
            findings.append(
                LeakageFinding(
                    code="AVAILABLE_AFTER_DECISION",
                    message=f"record available at {available.isoformat()} after decision {decision.isoformat()}",
                    record_repr=repr(record),
                )
            )
    return tuple(findings)


def assert_no_future_information(
    records: Iterable[AvailableRecord],
    *,
    decision_at: datetime,
) -> None:
    findings = scan_future_information(records, decision_at=decision_at)
    if findings:
        raise LeakageError(
            f"future information detected: {len(findings)} record(s); first={findings[0].message}"
        )


def assert_lineage_hashes(hashes: Iterable[str]) -> None:
    values = tuple(hashes)
    if not values:
        raise LeakageError("lineage hashes cannot be empty")
    for value in values:
        if len(value) != 64:
            raise LeakageError(f"invalid lineage hash: {value!r}")
        try:
            int(value, 16)
        except ValueError as exc:
            raise LeakageError(f"invalid lineage hash: {value!r}") from exc

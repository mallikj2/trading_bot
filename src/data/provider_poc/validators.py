from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import exp, isfinite, log, sqrt
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")


class ValidationError(ValueError):
    """Raised when a provider payload violates a fail-closed contract."""


@dataclass(frozen=True, slots=True)
class VwapResult:
    session_date: date
    symbol: str
    interval_count: int
    total_volume: int
    vwap: float


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError("datetime must be timezone-aware")
    return parsed.astimezone(UTC)


def validate_ticker_snapshot(
    rows: Sequence[Mapping[str, Any]],
    *,
    as_of_date: date,
    allowed_exchanges: set[str] | None = None,
    required_type: str = "CS",
) -> None:
    """Validate a point-in-time ticker snapshot without assuming current state."""
    allowed_exchanges = allowed_exchanges or {"XNYS", "XNAS"}
    if not rows:
        raise ValidationError("ticker snapshot is empty")

    seen_tickers: set[str] = set()
    seen_identity: set[tuple[str | None, str | None, str | None]] = set()

    for row in rows:
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            raise ValidationError("ticker is required")
        if ticker in seen_tickers:
            raise ValidationError(f"duplicate ticker in snapshot: {ticker}")
        seen_tickers.add(ticker)

        if row.get("type") != required_type:
            raise ValidationError(f"{ticker}: expected type {required_type}")
        if row.get("primary_exchange") not in allowed_exchanges:
            raise ValidationError(f"{ticker}: unsupported exchange")
        if row.get("active") is not True:
            raise ValidationError(f"{ticker}: snapshot row is not active on query date")

        identity = (
            row.get("share_class_figi"),
            row.get("composite_figi"),
            row.get("cik"),
        )
        if not any(identity):
            raise ValidationError(f"{ticker}: no stable identity field")
        if identity in seen_identity:
            raise ValidationError(f"{ticker}: duplicate identity tuple")
        seen_identity.add(identity)

        updated = row.get("last_updated_utc")
        if updated:
            updated_at = _parse_datetime(updated)
            if updated_at.date() < as_of_date:
                # Stale reference data is not necessarily wrong, but it must be visible.
                continue


def validate_intraday_vwap_window(
    rows: Sequence[Mapping[str, Any]],
    *,
    symbol: str,
    session_date: date,
    interval_minutes: int = 5,
) -> VwapResult:
    """Validate and calculate the 10:00-10:30 ET VWAP window."""
    if interval_minutes <= 0 or 30 % interval_minutes != 0:
        raise ValidationError("interval must divide the 30-minute window")

    expected_count = 30 // interval_minutes
    expected_times = {
        (datetime.combine(session_date, time(10, 0), NEW_YORK) + timedelta(minutes=i * interval_minutes)).time()
        for i in range(expected_count)
    }

    by_time: dict[time, Mapping[str, Any]] = {}
    for row in rows:
        timestamp_ms = row.get("t")
        if not isinstance(timestamp_ms, (int, float)):
            raise ValidationError("Massive aggregate timestamp 't' is required")
        local_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).astimezone(NEW_YORK)
        if local_dt.date() != session_date:
            continue
        local_time = local_dt.time().replace(tzinfo=None)
        if local_time not in expected_times:
            continue
        if local_time in by_time:
            raise ValidationError(f"duplicate intraday interval: {local_time}")
        by_time[local_time] = row

    missing = sorted(expected_times.difference(by_time))
    if missing:
        raise ValidationError(f"incomplete VWAP window; missing={missing}")

    weighted_sum = 0.0
    total_volume = 0
    for interval_time in sorted(by_time):
        row = by_time[interval_time]
        volume = row.get("v")
        interval_vwap = row.get("vw")
        if not isinstance(volume, int) or volume <= 0:
            raise ValidationError(f"zero or invalid volume at {interval_time}")
        if not isinstance(interval_vwap, (int, float)) or not isfinite(float(interval_vwap)) or interval_vwap <= 0:
            raise ValidationError(f"invalid interval VWAP at {interval_time}")
        weighted_sum += float(interval_vwap) * volume
        total_volume += volume

    if total_volume <= 0:
        raise ValidationError("VWAP window has no valid volume")

    return VwapResult(
        session_date=session_date,
        symbol=symbol,
        interval_count=expected_count,
        total_volume=total_volume,
        vwap=weighted_sum / total_volume,
    )


def select_pit_record(
    rows: Iterable[Mapping[str, Any]],
    *,
    decision_at: datetime,
    available_field: str = "available_at",
    revision_field: str = "revision",
) -> Mapping[str, Any]:
    """Select the latest record known by the decision timestamp."""
    decision_utc = _parse_datetime(decision_at)
    eligible: list[tuple[datetime, int, Mapping[str, Any]]] = []
    for row in rows:
        if available_field not in row:
            raise ValidationError(f"missing {available_field}")
        available_at = _parse_datetime(row[available_field])
        if available_at <= decision_utc:
            revision = int(row.get(revision_field, 0))
            eligible.append((available_at, revision, row))
    if not eligible:
        raise ValidationError("no point-in-time record was available")
    return max(eligible, key=lambda item: (item[0], item[1]))[2]


def validate_earnings_revisions(rows: Sequence[Mapping[str, Any]]) -> None:
    """Require a true known-at revision sequence rather than a current calendar."""
    if not rows:
        raise ValidationError("earnings revision dataset is empty")

    by_event: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        event_id = str(row.get("event_id", "")).strip()
        if not event_id:
            raise ValidationError("event_id is required")
        _parse_datetime(row.get("known_at", ""))
        timing = row.get("timing")
        if timing not in {"BMO", "AMC", "DURING_SESSION", "UNKNOWN"}:
            raise ValidationError(f"{event_id}: invalid timing")
        if "scheduled_date" not in row:
            raise ValidationError(f"{event_id}: scheduled_date is required")
        by_event.setdefault(event_id, []).append(row)

    for event_id, revisions in by_event.items():
        if len(revisions) < 2:
            raise ValidationError(f"{event_id}: no historical revision sequence")
        ordered = sorted(revisions, key=lambda row: _parse_datetime(row["known_at"]))
        known_times = [_parse_datetime(row["known_at"]) for row in ordered]
        if len(known_times) != len(set(known_times)):
            raise ValidationError(f"{event_id}: duplicate known_at timestamp")
        revision_numbers = [int(row.get("revision", -1)) for row in ordered]
        if revision_numbers != sorted(revision_numbers) or revision_numbers[0] < 0:
            raise ValidationError(f"{event_id}: invalid revision ordering")
        if not any(
            ordered[i].get("scheduled_date") != ordered[i - 1].get("scheduled_date")
            or ordered[i].get("timing") != ordered[i - 1].get("timing")
            or ordered[i].get("status") != ordered[i - 1].get("status")
            for i in range(1, len(ordered))
        ):
            raise ValidationError(f"{event_id}: versions contain no actual change")


def conservative_corwin_schultz_bps(
    *,
    high_t: float,
    low_t: float,
    high_prev: float,
    low_prev: float,
    floor_bps: float = 5.0,
) -> float:
    """Candidate modeled spread. It is not an observed quote."""
    values = (high_t, low_t, high_prev, low_prev)
    if any(not isfinite(v) or v <= 0 for v in values):
        raise ValidationError("high/low inputs must be finite and positive")
    if high_t < low_t or high_prev < low_prev:
        raise ValidationError("high cannot be below low")

    beta = log(high_t / low_t) ** 2 + log(high_prev / low_prev) ** 2
    gamma = log(max(high_t, high_prev) / min(low_t, low_prev)) ** 2
    denominator = 3.0 - 2.0 * sqrt(2.0)
    alpha = (
        (sqrt(2.0 * beta) - sqrt(beta)) / denominator
        - sqrt(gamma / denominator)
    )
    alpha = max(alpha, 0.0)
    exp_alpha = exp(alpha)
    raw_spread = 2.0 * (exp_alpha - 1.0) / (1.0 + exp_alpha)
    return max(float(floor_bps), 10_000.0 * raw_spread)

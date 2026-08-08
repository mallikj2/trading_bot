"""Approval-gated Databento companion adapter for Phase 02 provider trials.

Databento is evaluated as the point-in-time security-master and exact historical
execution-evidence companion. The import is intentionally lazy so the core repo
does not require the vendor SDK until the credentialed trial is actually run.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os
from typing import Any, Callable


class DatabentoCompanionError(RuntimeError):
    pass


class DatabentoLicenseError(PermissionError):
    pass


def _approved(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _default_reference_factory(api_key: str) -> Any:
    try:
        import databento as db  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only in credentialed environment
        raise DatabentoCompanionError(
            "Databento SDK is required for the credentialed companion trial; install the approved pinned version"
        ) from exc
    return db.Reference(api_key)


def _default_historical_factory(api_key: str) -> Any:
    try:
        import databento as db  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised only in credentialed environment
        raise DatabentoCompanionError(
            "Databento SDK is required for the credentialed companion trial; install the approved pinned version"
        ) from exc
    return db.Historical(api_key)


@dataclass(slots=True)
class DatabentoCompanionClient:
    api_key: str | None = None
    license_approved: bool | None = None
    reference_factory: Callable[[str], Any] = _default_reference_factory
    historical_factory: Callable[[str], Any] = _default_historical_factory

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("DATABENTO_API_KEY")
        env_approved = _approved(os.getenv("DATABENTO_RESEARCH_LICENSE_APPROVED"))
        self.license_approved = env_approved if self.license_approved is None else self.license_approved
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY is required")
        if not self.license_approved:
            raise DatabentoLicenseError(
                "Databento research-license approval flag is required before the PIT/execution companion trial"
            )

    def security_master_range(
        self,
        *,
        symbol: str,
        start: date | datetime | str,
        end: date | datetime | str | None = None,
    ) -> Any:
        if not symbol.strip():
            raise ValueError("symbol is required")
        client = self.reference_factory(str(self.api_key))
        kwargs: dict[str, Any] = {
            "symbols": [symbol],
            "countries": ["US"],
            "start": start,
            "index": "ts_effective",
        }
        if end is not None:
            kwargs["end"] = end
        return client.security_master.get_range(**kwargs)

    def historical_trades(
        self,
        *,
        dataset: str,
        symbol: str,
        start: datetime | str,
        end: datetime | str,
    ) -> Any:
        if not dataset.strip():
            raise ValueError("dataset is required and must be confirmed from the approved Databento account")
        if not symbol.strip():
            raise ValueError("symbol is required")
        client = self.historical_factory(str(self.api_key))
        return client.timeseries.get_range(
            dataset=dataset,
            schema="trades",
            symbols=[symbol],
            start=start,
            end=end,
        )


def dataframe_row_count(value: Any) -> int:
    """Return a deterministic row count for SDK DataFrame-like trial responses."""
    try:
        return int(len(value))
    except (TypeError, ValueError) as exc:
        raise DatabentoCompanionError("Databento response is not row-countable") from exc

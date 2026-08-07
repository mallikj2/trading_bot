"""Guarded ORTEX short-borrow evaluation adapter.

ORTEX is a technically capable candidate source, but the project's immutable
research archive is not authorized under ORTEX standard consumer terms.  This
client therefore requires an explicit research-license approval flag for any
non-demo API use.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from typing import Any, Mapping

from .http import JsonTransport, RetryPolicy, SafeJsonClient


class BorrowSourceLicenseError(RuntimeError):
    """Provider credentials exist but research/retention rights are not approved."""


@dataclass(frozen=True, slots=True)
class OrtexBorrowClientConfig:
    api_key: str
    research_license_approved: bool = False
    demo_mode: bool = False
    requests_per_second: float = 1.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("ORTEX api_key is required")
        if self.demo_mode and self.api_key != "TEST":
            raise ValueError("demo_mode requires the documented TEST key")
        if not self.demo_mode and not self.research_license_approved:
            raise BorrowSourceLicenseError(
                "ORTEX research/retention license is not approved for persistent Phase 02 use"
            )


class OrtexBorrowClient:
    BASE_URL = "https://api.ortex.com"

    def __init__(
        self,
        config: OrtexBorrowClientConfig | None = None,
        *,
        transport: JsonTransport | None = None,
        retry_policy: RetryPolicy | None = None,
        sleeper=lambda _: None,
    ) -> None:
        if config is None:
            key = os.getenv("ORTEX_API_KEY", "").strip()
            approved = os.getenv("ORTEX_RESEARCH_LICENSE_APPROVED", "").strip().lower() in {
                "1", "true", "yes"
            }
            config = OrtexBorrowClientConfig(api_key=key, research_license_approved=approved)
        self.config = config
        self.http = SafeJsonClient(
            base_url=self.BASE_URL,
            default_headers={
                "accept": "application/json",
                "Ortex-Api-Key": config.api_key,
            },
            transport=transport,
            requests_per_second=config.requests_per_second,
            retry_policy=retry_policy,
            sleeper=sleeper,
        )

    def cost_to_borrow(
        self,
        *,
        exchange_symbol: str,
        ticker: str,
        from_date: date,
        to_date: date,
        ticker_as_of_date: date,
    ) -> Mapping[str, Any]:
        if to_date < from_date:
            raise ValueError("to_date cannot precede from_date")
        return self.http.get_json(
            f"/api/v1/stock/{exchange_symbol}/{ticker}/ctb/all",
            params={
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "ticker_as_of_date": ticker_as_of_date.isoformat(),
                "format": "json",
            },
        )

    def short_availability_for_index(
        self,
        *,
        index_name: str,
        as_of_date: date,
        page: int = 1,
        page_size: int = 1000,
    ) -> Mapping[str, Any]:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        return self.http.get_json(
            "/api/v1/index/short_availability",
            params={
                "date": as_of_date.isoformat(),
                "index": index_name,
                "page": page,
                "page_size": page_size,
                "format": "json",
            },
        )

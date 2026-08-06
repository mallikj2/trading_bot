"""Production-oriented SEC EDGAR adapter for filing-timestamped share counts."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import os
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from ..contracts import DailyBar, MarketCapObservation
from ..errors import DataContractError, PointInTimeError
from ..pit import select_latest_known
from ..time_utils import require_aware
from .http import JsonTransport, SafeJsonClient
from .models import CurrentSicReference, SharesOutstandingObservation

UTC = timezone.utc
NEW_YORK = ZoneInfo("America/New_York")


class SecSchemaError(DataContractError):
    pass


class SecEdgarClient:
    base_url = "https://data.sec.gov"
    adapter_version = "SEC-EDGAR-v0.2.0"

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        transport: JsonTransport | None = None,
        requests_per_second: float = 5.0,
    ) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT")
        if not self.user_agent or "@" not in self.user_agent:
            raise ValueError(
                "SEC_USER_AGENT must identify the application and include a monitored contact email"
            )
        if requests_per_second > 10:
            raise ValueError("SEC fair-access limit is at most 10 requests per second")
        self._http = SafeJsonClient(
            base_url=self.base_url,
            default_headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
            transport=transport,
            requests_per_second=requests_per_second,
        )

    @staticmethod
    def normalize_cik(cik: str | int) -> str:
        try:
            numeric = int(str(cik))
        except ValueError as exc:
            raise ValueError("CIK must be numeric") from exc
        if numeric <= 0:
            raise ValueError("CIK must be positive")
        return f"{numeric:010d}"

    def submissions(self, cik: str | int) -> Mapping[str, Any]:
        return self._http.get_json(f"/submissions/CIK{self.normalize_cik(cik)}.json")

    def submissions_fragment(self, filename: str) -> Mapping[str, Any]:
        if "/" in filename or "\\" in filename or not filename.endswith(".json"):
            raise ValueError("invalid SEC submissions fragment filename")
        return self._http.get_json(f"/submissions/{filename}")

    def companyfacts(self, cik: str | int) -> Mapping[str, Any]:
        return self._http.get_json(f"/api/xbrl/companyfacts/CIK{self.normalize_cik(cik)}.json")


def _parse_sec_acceptance(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise SecSchemaError("SEC acceptance timestamp is blank")
    try:
        if "T" in text:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=NEW_YORK)
        elif len(text) == 14 and text.isdigit():
            parsed = datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=NEW_YORK)
        else:
            raise ValueError
    except ValueError as exc:
        raise SecSchemaError(f"invalid SEC acceptance timestamp: {value!r}") from exc
    return parsed.astimezone(UTC)


def _parallel_rows(mapping: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    if not mapping:
        return ()
    lengths = {len(value) for value in mapping.values() if isinstance(value, list)}
    if len(lengths) != 1:
        raise SecSchemaError("SEC submissions parallel arrays have inconsistent lengths")
    if not lengths:
        return ()
    count = next(iter(lengths))
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row = {
            key: value[index]
            for key, value in mapping.items()
            if isinstance(value, list)
        }
        rows.append(row)
    return tuple(rows)


def build_accession_acceptance_map(
    submissions_payload: Mapping[str, Any],
    *,
    older_fragments: Iterable[Mapping[str, Any]] = (),
) -> dict[str, datetime]:
    filings = submissions_payload.get("filings")
    if not isinstance(filings, Mapping):
        raise SecSchemaError("SEC submissions payload lacks filings")
    recent = filings.get("recent")
    if not isinstance(recent, Mapping):
        raise SecSchemaError("SEC submissions payload lacks filings.recent")

    rows = list(_parallel_rows(recent))
    for fragment in older_fragments:
        if not isinstance(fragment, Mapping):
            raise SecSchemaError("SEC submissions fragment must be an object")
        rows.extend(_parallel_rows(fragment))

    result: dict[str, datetime] = {}
    for row in rows:
        accession = str(row.get("accessionNumber", "")).strip()
        acceptance = str(row.get("acceptanceDateTime", "")).strip()
        if not accession:
            continue
        if not acceptance:
            # Filing dates alone are insufficient for the Phase 02 availability contract.
            continue
        parsed = _parse_sec_acceptance(acceptance)
        existing = result.get(accession)
        if existing is not None and existing != parsed:
            raise SecSchemaError(f"conflicting SEC acceptance timestamps for {accession}")
        result[accession] = parsed
    if not result:
        raise SecSchemaError("no filing acceptance timestamps were available")
    return result


_SHARE_CONCEPTS = (
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "CommonStockSharesOutstanding"),
)
_ALLOWED_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A", "8-K", "8-K/A", "6-K", "6-K/A"}


def extract_shares_outstanding(
    companyfacts_payload: Mapping[str, Any],
    *,
    instrument_id: UUID,
    accession_acceptance: Mapping[str, datetime],
    source_snapshot_id: str,
    processing_buffer: timedelta = timedelta(minutes=1),
) -> tuple[SharesOutstandingObservation, ...]:
    if processing_buffer < timedelta(0):
        raise ValueError("processing_buffer cannot be negative")
    facts = companyfacts_payload.get("facts")
    if not isinstance(facts, Mapping):
        raise SecSchemaError("SEC companyfacts payload lacks facts")

    candidates: list[SharesOutstandingObservation] = []
    for taxonomy, concept in _SHARE_CONCEPTS:
        taxonomy_map = facts.get(taxonomy)
        if not isinstance(taxonomy_map, Mapping):
            continue
        concept_map = taxonomy_map.get(concept)
        if not isinstance(concept_map, Mapping):
            continue
        units = concept_map.get("units")
        if not isinstance(units, Mapping):
            raise SecSchemaError(f"SEC fact {taxonomy}:{concept} lacks units")
        share_rows = units.get("shares")
        if not isinstance(share_rows, Sequence) or isinstance(share_rows, (str, bytes, bytearray)):
            continue
        for row in share_rows:
            if not isinstance(row, Mapping):
                raise SecSchemaError("SEC fact unit row must be an object")
            accession = str(row.get("accn", "")).strip()
            accepted_at = accession_acceptance.get(accession)
            if not accession or accepted_at is None:
                continue
            form = str(row.get("form", "")).strip()
            if form and form not in _ALLOWED_FORMS:
                continue
            end_value = row.get("end")
            filed_value = row.get("filed")
            if not end_value or not filed_value:
                continue
            try:
                shares = Decimal(str(row.get("val")))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise SecSchemaError(f"SEC shares fact is not numeric for {accession}") from exc
            candidates.append(
                SharesOutstandingObservation(
                    instrument_id=instrument_id,
                    period_end=date.fromisoformat(str(end_value)),
                    shares_outstanding=shares,
                    accession_number=accession,
                    form_type=form or "UNKNOWN",
                    filed_date=date.fromisoformat(str(filed_value)),
                    accepted_at=accepted_at,
                    available_at=accepted_at + processing_buffer,
                    source_snapshot_id=source_snapshot_id,
                    concept=concept,
                    taxonomy=taxonomy,
                    revision=1 if form.endswith("/A") else 0,
                )
            )

    if not candidates:
        raise SecSchemaError("no filing-timestamped shares-outstanding facts were found")

    # Fail closed where different facts in the same filing describe the same period
    # with conflicting values; this commonly signals class/member ambiguity.
    by_key: dict[tuple[str, date], list[SharesOutstandingObservation]] = defaultdict(list)
    for item in candidates:
        by_key[(item.accession_number, item.period_end)].append(item)
    for key, values in by_key.items():
        distinct = {item.shares_outstanding for item in values}
        if len(distinct) > 1:
            raise SecSchemaError(
                f"ambiguous multi-class shares facts for accession={key[0]} period={key[1]}"
            )

    deduped: dict[tuple[str, date, Decimal], SharesOutstandingObservation] = {}
    for item in candidates:
        key = (item.accession_number, item.period_end, item.shares_outstanding)
        current = deduped.get(key)
        if current is None or (item.taxonomy == "dei" and current.taxonomy != "dei"):
            deduped[key] = item
    return tuple(
        sorted(
            deduped.values(),
            key=lambda item: (item.available_at, item.period_end, item.accession_number, item.taxonomy),
        )
    )


def select_shares_as_of(
    observations: Iterable[SharesOutstandingObservation],
    *,
    decision_at: datetime,
) -> SharesOutstandingObservation:
    decision = require_aware(decision_at, "decision_at")
    eligible = [
        item
        for item in observations
        if item.period_end <= decision.date() and item.available_at <= decision
    ]
    if not eligible:
        raise PointInTimeError("no shares-outstanding fact was available by the decision timestamp")
    latest_period = max(item.period_end for item in eligible)
    return select_latest_known(
        eligible,
        decision_at=decision,
        predicate=lambda item: item.period_end == latest_period,
    )


def derive_market_cap(
    *,
    instrument_id: UUID,
    raw_close_bar: DailyBar,
    shares: SharesOutstandingObservation,
    decision_at: datetime,
    source_snapshot_id: str,
) -> MarketCapObservation:
    decision = require_aware(decision_at, "decision_at")
    if raw_close_bar.instrument_id != instrument_id or shares.instrument_id != instrument_id:
        raise DataContractError("market-cap inputs must reference the same instrument")
    if raw_close_bar.available_at > decision or shares.available_at > decision:
        raise PointInTimeError("market-cap input was not available at the decision timestamp")
    available_at = max(raw_close_bar.available_at, shares.available_at)
    return MarketCapObservation(
        instrument_id=instrument_id,
        observed_at=raw_close_bar.observed_at,
        available_at=available_at,
        market_cap=raw_close_bar.close * shares.shares_outstanding,
        source_snapshot_id=source_snapshot_id,
        revision=max(raw_close_bar.provider_revision, shares.revision),
    )


def extract_current_sic_reference(
    submissions_payload: Mapping[str, Any],
    *,
    retrieved_at: datetime,
    source_snapshot_id: str,
) -> CurrentSicReference:
    raw_cik = str(submissions_payload.get("cik", "")).strip()
    if not raw_cik or not raw_cik.isdigit() or int(raw_cik) <= 0:
        raise SecSchemaError("SEC submissions payload lacks a valid CIK")
    cik = raw_cik.zfill(10)
    sic = str(submissions_payload.get("sic", "")).strip()
    description = str(submissions_payload.get("sicDescription", "")).strip()
    if not sic:
        raise SecSchemaError("SEC submissions payload lacks current SIC")
    return CurrentSicReference(
        cik=cik,
        sic_code=sic,
        sic_description=description,
        retrieved_at=retrieved_at,
        source_snapshot_id=source_snapshot_id,
    )


def historical_sector_from_submissions(*_: Any, **__: Any) -> None:
    raise PointInTimeError(
        "SEC submissions top-level SIC is current-state metadata and cannot satisfy historical sector PIT requirements"
    )

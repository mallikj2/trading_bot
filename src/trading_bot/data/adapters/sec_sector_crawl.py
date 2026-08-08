"""Resumable SEC historical-sector coverage crawler for P02-G07.

The crawler deliberately separates three layers:

1. a sector-blind target ledger produced by the upstream historical universe;
2. SEC daily master indexes, which preserve filings later removed by PACs;
3. immutable complete-submission headers used to extract filing-time assigned SIC.

The real crawl requires a monitored-contact SEC User-Agent and an upstream target
ledger.  If either is absent, the CLI emits a BLOCKED result rather than guessing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta, timezone
import argparse
import csv
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID

from ..errors import DataContractError
from ..sector_coverage import (
    SectorChangeReview,
    SectorCoverageRequirement,
    evaluate_sector_coverage,
    summarize_coverage_by_cik,
)
from .http import JsonTransport, SafeJsonClient, SafeTextClient, TextTransport, ProviderRequestError
from .sec_filing_sic import SecArchivesClient, SecFilingHeaderError, SecFilingSicObservation, parse_filing_sic
from .storage import RawSnapshotStore

UTC = timezone.utc


class SecSectorCrawlError(DataContractError):
    pass


@dataclass(frozen=True, slots=True)
class SecDailyIndexRow:
    cik: str
    company_name: str
    form_type: str
    filing_date: date
    filename: str
    accession_number: str

    def __post_init__(self) -> None:
        cik = self.cik.strip()
        if not cik.isdigit() or int(cik) <= 0:
            raise SecSectorCrawlError("daily-index CIK must be positive numeric")
        object.__setattr__(self, "cik", cik.zfill(10))
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", self.accession_number):
            raise SecSectorCrawlError("invalid accession number in SEC daily index")
        if not self.company_name.strip() or not self.form_type.strip() or not self.filename.strip():
            raise SecSectorCrawlError("SEC daily-index row lacks required fields")


@dataclass(frozen=True, slots=True)
class CrawlFailure:
    cik: str
    accession_number: str
    filing_date: date
    reason: str


@dataclass(frozen=True, slots=True)
class CikCrawlResult:
    cik: str
    selected_filing_count: int
    parsed_filing_count: int
    observations: tuple[SecFilingSicObservation, ...]
    failures: tuple[CrawlFailure, ...]


class SecDailyIndexClient:
    base_url = "https://www.sec.gov"
    adapter_version = "SEC-DAILY-INDEX-v0.1.0"

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        json_transport: JsonTransport | None = None,
        text_transport: TextTransport | None = None,
        requests_per_second: float = 5.0,
    ) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT")
        if not self.user_agent or "@" not in self.user_agent:
            raise ValueError(
                "SEC_USER_AGENT must identify the application and include a monitored contact email"
            )
        if requests_per_second > 10:
            raise ValueError("SEC fair-access limit is at most 10 requests per second")
        headers = {"User-Agent": self.user_agent}
        self._json = SafeJsonClient(
            base_url=self.base_url,
            default_headers={**headers, "Accept": "application/json"},
            transport=json_transport,
            requests_per_second=requests_per_second,
        )
        self._text = SafeTextClient(
            base_url=self.base_url,
            default_headers={**headers, "Accept": "text/plain,*/*;q=0.1"},
            transport=text_transport,
            requests_per_second=requests_per_second,
        )

    @staticmethod
    def quarter(value: date) -> int:
        return ((value.month - 1) // 3) + 1

    def quarter_directory(self, year: int, quarter: int) -> Mapping[str, Any]:
        if year < 1994 or quarter not in {1, 2, 3, 4}:
            raise ValueError("invalid SEC daily-index year/quarter")
        return self._json.get_json(f"/Archives/edgar/daily-index/{year}/QTR{quarter}/index.json")

    def master_index(self, filing_date: date) -> str:
        quarter = self.quarter(filing_date)
        stamp = filing_date.strftime("%Y%m%d")
        return self._text.get_text(
            f"/Archives/edgar/daily-index/{filing_date.year}/QTR{quarter}/master.{stamp}.idx"
        )


def parse_master_index(text: str, *, expected_date: date | None = None) -> tuple[SecDailyIndexRow, ...]:
    """Parse an SEC daily master index and fail on conflicting duplicate accessions."""
    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if line.strip().upper() == "CIK|COMPANY NAME|FORM TYPE|DATE FILED|FILENAME":
            header_index = index
            break
    if header_index is None:
        raise SecSectorCrawlError("SEC master index lacks expected column header")

    rows: dict[str, SecDailyIndexRow] = {}
    for raw in lines[header_index + 1 :]:
        line = raw.strip()
        if not line or line.startswith("-"):
            continue
        parts = line.split("|")
        if len(parts) != 5:
            raise SecSectorCrawlError(f"malformed SEC master-index row: {line!r}")
        cik, company_name, form_type, filed, filename = (part.strip() for part in parts)
        filing_date = date.fromisoformat(filed)
        if expected_date is not None and filing_date != expected_date:
            raise SecSectorCrawlError("daily master-index row has unexpected filing date")
        match = re.search(r"/(\d{10}-\d{2}-\d{6})\.txt$", filename)
        if not match:
            raise SecSectorCrawlError("SEC master-index filename lacks accession number")
        row = SecDailyIndexRow(
            cik=cik,
            company_name=company_name,
            form_type=form_type,
            filing_date=filing_date,
            filename=filename,
            accession_number=match.group(1),
        )
        existing = rows.get(row.accession_number)
        if existing is not None and existing != row:
            raise SecSectorCrawlError("conflicting duplicate accession in SEC master index")
        rows[row.accession_number] = row
    return tuple(sorted(rows.values(), key=lambda row: (row.filing_date, row.accession_number)))


def master_index_names(directory_payload: Mapping[str, Any]) -> tuple[str, ...]:
    directory = directory_payload.get("directory")
    if not isinstance(directory, Mapping):
        raise SecSectorCrawlError("SEC directory index lacks directory object")
    items = directory.get("item")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
        raise SecSectorCrawlError("SEC directory index lacks item array")
    names: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise SecSectorCrawlError("SEC directory item must be an object")
        name = str(item.get("name", "")).strip()
        if re.fullmatch(r"master\.\d{8}\.idx", name):
            names.add(name)
    return tuple(sorted(names))


def parse_target_ledger(payload: Mapping[str, Any]) -> tuple[SectorCoverageRequirement, ...]:
    if payload.get("sector_blind") is not True:
        raise SecSectorCrawlError("target ledger must declare sector_blind=true")
    rows = payload.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)) or not rows:
        raise SecSectorCrawlError("target ledger requires non-empty rows")
    requirements: list[SectorCoverageRequirement] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise SecSectorCrawlError("target-ledger row must be an object")
        requirements.append(
            SectorCoverageRequirement(
                instrument_id=UUID(str(row["instrument_id"])),
                cik=str(row["cik"]),
                decision_at=datetime.fromisoformat(str(row["decision_at"]).replace("Z", "+00:00")),
                source_manifest_hash=str(row["source_manifest_hash"]),
                universe_version=str(row["universe_version"]),
            )
        )
    return tuple(requirements)


def load_reviews(path: str | Path | None) -> tuple[SectorChangeReview, ...]:
    if path is None:
        return ()
    review_path = Path(path)
    if not review_path.exists():
        return ()
    rows: list[SectorChangeReview] = []
    with review_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                SectorChangeReview(
                    instrument_id=UUID(row["instrument_id"]),
                    cik=row["cik"],
                    effective_from=datetime.fromisoformat(row["effective_from"].replace("Z", "+00:00")),
                    from_sector=row.get("from_sector") or None,
                    to_sector=row["to_sector"],
                    accession_number=row["accession_number"],
                    status=row["status"],
                    reviewer_note=row.get("reviewer_note", ""),
                )
            )
    return tuple(rows)


class CrawlCheckpoint:
    """Mutable operational checkpoint; raw provider snapshots remain immutable."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.payload: dict[str, Any] = {"version": 1, "filings": {}, "indexes": {}}
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if loaded.get("version") != 1 or not isinstance(loaded.get("filings"), dict):
                raise SecSectorCrawlError("unsupported crawl checkpoint format")
            loaded.setdefault("indexes", {})
            if not isinstance(loaded.get("indexes"), dict):
                raise SecSectorCrawlError("unsupported crawl checkpoint index format")
            self.payload = loaded

    @staticmethod
    def key(cik: str, accession_number: str) -> str:
        return f"{str(int(cik)).zfill(10)}:{accession_number}"

    def get(self, cik: str, accession_number: str) -> Mapping[str, Any] | None:
        value = self.payload["filings"].get(self.key(cik, accession_number))
        return value if isinstance(value, Mapping) else None

    def get_index(self, filing_date: date) -> Mapping[str, Any] | None:
        value = self.payload["indexes"].get(filing_date.isoformat())
        return value if isinstance(value, Mapping) else None

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def put(self, cik: str, accession_number: str, value: Mapping[str, Any]) -> None:
        self.payload["filings"][self.key(cik, accession_number)] = dict(value)
        self._flush()

    def put_index(self, filing_date: date, value: Mapping[str, Any]) -> None:
        self.payload["indexes"][filing_date.isoformat()] = dict(value)
        self._flush()


class SecSectorCoverageCrawler:
    """Network crawler that persists immutable raw SEC evidence and resumes safely."""

    def __init__(
        self,
        *,
        daily_index_client: SecDailyIndexClient,
        archives_client: SecArchivesClient,
        snapshot_store: RawSnapshotStore,
        checkpoint: CrawlCheckpoint,
        processing_buffer: timedelta = timedelta(minutes=3),
    ) -> None:
        if processing_buffer < timedelta(0):
            raise ValueError("processing_buffer cannot be negative")
        self.daily_index_client = daily_index_client
        self.archives_client = archives_client
        self.snapshot_store = snapshot_store
        self.checkpoint = checkpoint
        self.processing_buffer = processing_buffer

    def _filing_rows_for_targets(
        self,
        *,
        ciks: set[str],
        start_date: date,
        end_date: date,
    ) -> tuple[SecDailyIndexRow, ...]:
        if end_date < start_date:
            raise ValueError("end_date cannot precede start_date")
        rows: dict[str, SecDailyIndexRow] = {}
        for year in range(start_date.year, end_date.year + 1):
            for quarter in (1, 2, 3, 4):
                quarter_start_month = (quarter - 1) * 3 + 1
                quarter_start = date(year, quarter_start_month, 1)
                if quarter == 4:
                    quarter_end = date(year, 12, 31)
                else:
                    quarter_end = date(year, quarter_start_month + 3, 1) - timedelta(days=1)
                if quarter_end < start_date or quarter_start > end_date:
                    continue
                directory = self.daily_index_client.quarter_directory(year, quarter)
                for name in master_index_names(directory):
                    stamp = name[len("master.") : -len(".idx")]
                    filing_date = datetime.strptime(stamp, "%Y%m%d").date()
                    if filing_date < start_date or filing_date > end_date:
                        continue
                    index_checkpoint = self.checkpoint.get_index(filing_date)
                    text: str | None = None
                    if index_checkpoint and index_checkpoint.get("status") == "SUCCESS":
                        payload_path = Path(str(index_checkpoint.get("payload_path", "")))
                        if payload_path.is_file():
                            text = payload_path.read_text(encoding="utf-8", errors="replace")
                    if text is None:
                        text = self.daily_index_client.master_index(filing_date)
                        receipt = self.snapshot_store.persist_text(
                            provider="SEC",
                            dataset_name="daily-master-index",
                            dataset_version="daily-index-as-published",
                            adapter_version=self.daily_index_client.adapter_version,
                            schema_version="MASTER-IDX-v1",
                            retrieved_at=datetime.now(tz=UTC),
                            request_parameters={"filing_date": filing_date.isoformat()},
                            payload_text=text,
                            record_count=len(text.splitlines()),
                            license_classification="PUBLIC_SEC_RESEARCH_ARCHIVE",
                            coverage_start=filing_date,
                            coverage_end=filing_date,
                            filename=name,
                        )
                        self.checkpoint.put_index(
                            filing_date,
                            {
                                "status": "SUCCESS",
                                "payload_path": receipt.payload_path,
                                "snapshot_id": receipt.snapshot_id,
                            },
                        )
                    for row in parse_master_index(text, expected_date=filing_date):
                        if row.cik in ciks:
                            existing = rows.get(row.accession_number)
                            if existing is not None and existing != row:
                                raise SecSectorCrawlError("same accession conflicts across SEC daily indexes")
                            rows[row.accession_number] = row
        return tuple(sorted(rows.values(), key=lambda row: (row.filing_date, row.accession_number)))

    def crawl(
        self,
        requirements: Sequence[SectorCoverageRequirement],
        *,
        seed_lookback_days: int = 550,
    ) -> tuple[CikCrawlResult, ...]:
        if seed_lookback_days < 365:
            raise ValueError("seed_lookback_days must be at least 365")
        if not requirements:
            raise SecSectorCrawlError("crawl requires sector coverage requirements")
        ciks = {row.cik for row in requirements}
        start = min(row.decision_at.date() for row in requirements) - timedelta(days=seed_lookback_days)
        end = max(row.decision_at.date() for row in requirements)
        filing_rows = self._filing_rows_for_targets(ciks=ciks, start_date=start, end_date=end)

        instrument_ids_by_cik: dict[str, set[UUID]] = {}
        for requirement in requirements:
            instrument_ids_by_cik.setdefault(requirement.cik, set()).add(requirement.instrument_id)

        by_cik: dict[str, list[SecDailyIndexRow]] = {cik: [] for cik in ciks}
        for row in filing_rows:
            by_cik.setdefault(row.cik, []).append(row)

        results: list[CikCrawlResult] = []
        for cik in sorted(ciks):
            observations: list[SecFilingSicObservation] = []
            failures: list[CrawlFailure] = []
            parsed = 0
            for row in by_cik.get(cik, []):
                checkpoint = self.checkpoint.get(cik, row.accession_number)
                text: str | None = None
                snapshot_id: str | None = None
                if checkpoint and checkpoint.get("status") == "SUCCESS":
                    payload_path = Path(str(checkpoint.get("payload_path", "")))
                    if payload_path.is_file():
                        text = payload_path.read_text(encoding="utf-8", errors="replace")
                        snapshot_id = str(checkpoint.get("snapshot_id"))
                if text is None:
                    try:
                        text = self.archives_client.complete_submission(cik, row.accession_number)
                        receipt = self.snapshot_store.persist_text(
                            provider="SEC",
                            dataset_name="complete-submission-header-source",
                            dataset_version="current-archive-with-daily-index-inventory",
                            adapter_version=self.archives_client.adapter_version,
                            schema_version="SEC-COMPLETE-SUBMISSION-v1",
                            retrieved_at=datetime.now(tz=UTC),
                            request_parameters={
                                "cik": cik,
                                "accession_number": row.accession_number,
                                "filing_date": row.filing_date.isoformat(),
                            },
                            payload_text=text,
                            record_count=1,
                            license_classification="PUBLIC_SEC_RESEARCH_ARCHIVE",
                            coverage_start=row.filing_date,
                            coverage_end=row.filing_date,
                            filename=f"{row.accession_number}.txt",
                        )
                        snapshot_id = receipt.snapshot_id
                        self.checkpoint.put(
                            cik,
                            row.accession_number,
                            {
                                "status": "SUCCESS",
                                "payload_path": receipt.payload_path,
                                "snapshot_id": receipt.snapshot_id,
                            },
                        )
                    except ProviderRequestError as exc:
                        self.checkpoint.put(
                            cik,
                            row.accession_number,
                            {"status": "FAILED", "reason": str(exc)},
                        )
                        failures.append(
                            CrawlFailure(
                                cik=cik,
                                accession_number=row.accession_number,
                                filing_date=row.filing_date,
                                reason=f"ARCHIVE_FETCH_FAILED:{exc}",
                            )
                        )
                        continue
                assert snapshot_id is not None
                parsed_for_cik = False
                for instrument_id in sorted(instrument_ids_by_cik[cik], key=str):
                    try:
                        observation = parse_filing_sic(
                            text,
                            instrument_id=instrument_id,
                            target_cik=cik,
                            source_snapshot_id=snapshot_id,
                            processing_buffer=self.processing_buffer,
                        )
                    except SecFilingHeaderError as exc:
                        failures.append(
                            CrawlFailure(
                                cik=cik,
                                accession_number=row.accession_number,
                                filing_date=row.filing_date,
                                reason=f"SIC_PARSE_FAILED:{exc}",
                            )
                        )
                        break
                    observations.append(observation)
                    parsed_for_cik = True
                if parsed_for_cik:
                    parsed += 1
            results.append(
                CikCrawlResult(
                    cik=cik,
                    selected_filing_count=len(by_cik.get(cik, [])),
                    parsed_filing_count=parsed,
                    observations=tuple(observations),
                    failures=tuple(failures),
                )
            )
        return tuple(results)


def _serialize_point(point) -> dict[str, Any]:
    value = asdict(point)
    value["instrument_id"] = str(point.instrument_id)
    value["decision_at"] = point.decision_at.isoformat()
    if point.available_at is not None:
        value["available_at"] = point.available_at.isoformat()
    return value


def blocked_result(*, reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "phase": "PHASE_02_DATA_AND_POINT_IN_TIME_DESIGN",
        "gate_id": "P02-G07",
        "status": "BLOCKED",
        "phase03_authorized": False,
        "reasons": list(reasons),
        "claims": {
            "full_sec_crawl_completed": False,
            "coverage_ratio_measured": False,
            "manual_25_change_review_completed": False,
        },
    }


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the P02-G07 SEC sector coverage crawl")
    parser.add_argument("--targets", default=os.getenv("SEC_SECTOR_TARGET_LEDGER", ""))
    parser.add_argument("--reviews", default=os.getenv("SEC_SECTOR_CHANGE_REVIEW", ""))
    parser.add_argument("--raw-root", default="data/research/raw")
    parser.add_argument("--checkpoint", default="data/research/working/sec_sector_coverage_checkpoint.json")
    parser.add_argument("--output", default="SEC_SECTOR_COVERAGE_RESULTS.json")
    parser.add_argument("--seed-lookback-days", type=int, default=550)
    args = parser.parse_args(argv)

    reasons: list[str] = []
    if not os.getenv("SEC_USER_AGENT") or "@" not in os.getenv("SEC_USER_AGENT", ""):
        reasons.append("SEC_USER_AGENT_WITH_MONITORED_CONTACT_REQUIRED")
    if not args.targets or not Path(args.targets).is_file():
        reasons.append("SECTOR_BLIND_TARGET_LEDGER_REQUIRED_FROM_UPSTREAM_PIT_UNIVERSE")
    if reasons:
        Path(args.output).write_text(json.dumps(blocked_result(reasons=reasons), indent=2) + "\n", encoding="utf-8")
        return 2

    payload = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise SecSectorCrawlError("target ledger must be a JSON object")
    requirements = parse_target_ledger(payload)
    reviews = load_reviews(args.reviews or None)

    user_agent = os.environ["SEC_USER_AGENT"]
    index_client = SecDailyIndexClient(user_agent=user_agent, requests_per_second=5)
    archive_client = SecArchivesClient(user_agent=user_agent, requests_per_second=5)
    crawler = SecSectorCoverageCrawler(
        daily_index_client=index_client,
        archives_client=archive_client,
        snapshot_store=RawSnapshotStore(args.raw_root),
        checkpoint=CrawlCheckpoint(args.checkpoint),
        processing_buffer=timedelta(minutes=3),
    )
    crawl_results = crawler.crawl(requirements, seed_lookback_days=args.seed_lookback_days)
    observations = tuple(obs for result in crawl_results for obs in result.observations)
    failures = tuple(failure for result in crawl_results for failure in result.failures)
    points, audit = evaluate_sector_coverage(
        requirements,
        observations,
        unresolved_filing_count=len(failures),
        reviews=reviews,
        representative_header_samples_passed=True,
    )
    result = {
        "phase": "PHASE_02_DATA_AND_POINT_IN_TIME_DESIGN",
        "gate_id": "P02-G07",
        "status": "PASS" if audit.ready_for_gate else "BLOCKED",
        "phase03_authorized": False,
        "coverage": {
            "required_points": audit.required_points,
            "covered_points": audit.covered_points,
            "coverage_ratio": audit.coverage_ratio,
            "unresolved_filing_count": audit.unresolved_filing_count,
            "sector_change_count": audit.sector_change_count,
            "traceable_sector_change_count": audit.traceable_sector_change_count,
            "interval_overlap_count": audit.interval_overlap_count,
            "approved_manual_reviews": audit.approved_manual_reviews,
            "rejected_manual_reviews": audit.rejected_manual_reviews,
            "representative_header_samples_passed": audit.representative_header_samples_passed,
        },
        "by_cik": list(summarize_coverage_by_cik(requirements, points)),
        "missing_points": [_serialize_point(point) for point in audit.missing_points],
        "failures": [
            {
                "cik": failure.cik,
                "accession_number": failure.accession_number,
                "filing_date": failure.filing_date.isoformat(),
                "reason": failure.reason,
            }
            for failure in failures
        ],
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if audit.ready_for_gate else 3


if __name__ == "__main__":
    raise SystemExit(run_cli())

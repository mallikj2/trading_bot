"""Credentialed/export-based corporate-action representative trial for Phase 02.

EDI authentication is deliberately not guessed.  The EDI leg consumes a raw
trial export obtained under the approved client agreement.  Databento can be
queried directly through the approval-gated Reference API client.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import csv
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import UUID, uuid5, NAMESPACE_URL

from ..contracts import CorporateAction, CorporateActionType
from ..corporate_action_reconciliation import ReconciliationStatus, reconcile_action_set
from .databento_corporate_actions import DatabentoCorporateActionsClient, parse_databento_evidence
from .edi_corporate_actions import parse_edi_evidence

UTC = timezone.utc

EVENTS_BY_ACTION: dict[CorporateActionType, list[str]] = {
    CorporateActionType.SPLIT: ["FSPLT"],
    CorporateActionType.REVERSE_SPLIT: ["RSPLT"],
    CorporateActionType.SPINOFF: ["DMRGR", "SOFF", "DIST"],
    CorporateActionType.MERGER: ["MRGR", "TKOVR"],
    CorporateActionType.ACQUISITION: ["MRGR", "TKOVR"],
    CorporateActionType.BANKRUPTCY: ["BKRP", "LIQ", "LSTAT"],
}


def _approved(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def environment_status() -> dict[str, Any]:
    edi_path = os.getenv("EDI_CORPORATE_ACTIONS_EXPORT_PATH", "").strip()
    return {
        "preferred_long_history_provider": "EDI_WCA",
        "preferred_pit_overlap_provider": "DATABENTO_CA",
        "edi_export_path": edi_path or "MISSING",
        "edi_export_present": bool(edi_path and Path(edi_path).is_file()),
        "edi_license_approved": _approved("EDI_CORPORATE_ACTIONS_LICENSE_APPROVED"),
        "databento_api_key": "AVAILABLE" if os.getenv("DATABENTO_API_KEY") else "MISSING",
        "databento_license_approved": _approved("DATABENTO_CORPORATE_ACTIONS_LICENSE_APPROVED"),
    }


def load_golden_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("golden-case file must contain a non-empty cases list")
    return cases


def _load_export_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("rows") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("EDI JSON export must be a list or contain a rows list")
        return [dict(row) for row in rows]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _instrument_id(case_id: str, suffix: str = "source") -> UUID:
    return uuid5(NAMESPACE_URL, f"phase02-corporate-action:{case_id}:{suffix}")


def action_from_case(case: Mapping[str, Any]) -> CorporateAction:
    action_type = CorporateActionType(str(case["action_type"]))
    effective = datetime.combine(date.fromisoformat(str(case["effective_date"])), datetime.min.time(), tzinfo=UTC)
    kwargs: dict[str, Any] = {
        "action_id": str(case["case_id"]),
        "instrument_id": _instrument_id(str(case["case_id"])),
        "action_type": action_type,
        "effective_at": effective,
        "available_at": effective,
        "source_snapshot_id": "OFFICIAL_GOLDEN_CASE",
    }
    if "split_old_shares" in case:
        kwargs["split_old_shares"] = Decimal(str(case["split_old_shares"]))
        kwargs["split_new_shares"] = Decimal(str(case["split_new_shares"]))
    if "stock_ratio" in case:
        kwargs["stock_ratio"] = Decimal(str(case["stock_ratio"]))
        if action_type == CorporateActionType.SPINOFF:
            kwargs["child_instrument_id"] = _instrument_id(str(case["case_id"]), "child")
        elif action_type in {CorporateActionType.MERGER, CorporateActionType.ACQUISITION}:
            kwargs["successor_instrument_id"] = _instrument_id(str(case["case_id"]), "successor")
    if "cash_amount" in case:
        kwargs["cash_amount"] = Decimal(str(case["cash_amount"]))
        kwargs["currency"] = str(case["currency"])
    return CorporateAction(**kwargs)


def _records_from_result(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    if hasattr(result, "to_df"):
        frame = result.to_df()
        return [dict(row) for row in frame.to_dict(orient="records")]
    if hasattr(result, "to_dict"):
        try:
            records = result.to_dict(orient="records")
            if isinstance(records, list):
                return [dict(row) for row in records]
        except TypeError:
            pass
    if isinstance(result, Mapping):
        return [dict(result)]
    if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
        return [dict(row) for row in result if isinstance(row, Mapping)]
    raise TypeError("unsupported provider result shape")


def run_edi_export_trial(*, golden_cases: list[dict[str, Any]], export_path: Path) -> dict[str, Any]:
    if not _approved("EDI_CORPORATE_ACTIONS_LICENSE_APPROVED"):
        return {"status": "BLOCKED", "reason": "EDI_CORPORATE_ACTIONS_LICENSE_APPROVED is not true", "cases": []}
    rows = _load_export_rows(export_path)
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        case_id = str(row.get("case_id") or row.get("_case_id") or "").strip()
        if case_id:
            by_case.setdefault(case_id, []).append(row)

    case_results: list[dict[str, Any]] = []
    for case in golden_cases:
        case_id = str(case["case_id"])
        action_type = CorporateActionType(str(case["action_type"]))
        source_rows = by_case.get(case_id, [])
        evidence = []
        parse_errors: list[str] = []
        for row in source_rows:
            try:
                evidence.append(parse_edi_evidence(
                    row,
                    action_type=action_type,
                    source_snapshot_id=str(row.get("source_snapshot_id") or export_path.name),
                    ratio_semantics=str(row.get("ratio_semantics") or "TOTAL_NEW_OVER_OLD"),
                ))
            except Exception as exc:
                parse_errors.append(type(exc).__name__)
        if parse_errors:
            case_results.append({"case_id": case_id, "status": "FAIL", "parse_errors": parse_errors})
            continue
        result = reconcile_action_set([action_from_case(case)], evidence)[0]
        case_results.append({
            "case_id": case_id,
            "status": result.status.value,
            "provider_event_id": result.provider_event_id,
            "reasons": list(result.reasons),
        })
    overall = "PASS" if case_results and all(row["status"] == "PASS" for row in case_results) else "BLOCKED"
    return {"status": overall, "provider": "EDI_WCA", "cases": case_results, "export_path": str(export_path)}


def run_databento_overlap_trial(*, golden_cases: list[dict[str, Any]], client: DatabentoCorporateActionsClient | None = None) -> dict[str, Any]:
    if not os.getenv("DATABENTO_API_KEY") or not _approved("DATABENTO_CORPORATE_ACTIONS_LICENSE_APPROVED"):
        return {"status": "BLOCKED", "reason": "Databento API key and explicit corporate-actions license approval are required", "cases": []}
    client = client or DatabentoCorporateActionsClient()
    case_results: list[dict[str, Any]] = []
    for case in golden_cases:
        action_type = CorporateActionType(str(case["action_type"]))
        effective = date.fromisoformat(str(case["effective_date"]))
        # Databento coverage starts in 2018; every current golden case is inside
        # the overlap window. Query a broad window so pre-effective revisions are
        # included and retain PIT revisions via pit=True.
        raw = client.get_range(
            symbols=str(case["symbol"]),
            start=effective - timedelta(days=180),
            end=effective + timedelta(days=30),
            events=EVENTS_BY_ACTION.get(action_type),
            pit=True,
        )
        evidence = []
        parse_errors: list[str] = []
        for row in _records_from_result(raw):
            try:
                evidence.append(parse_databento_evidence(
                    row,
                    action_type=action_type,
                    source_snapshot_id="DATABENTO_CA_CREDENTIALED_TRIAL",
                ))
            except Exception as exc:
                parse_errors.append(type(exc).__name__)
        if parse_errors and not evidence:
            case_results.append({"case_id": case["case_id"], "status": "FAIL", "parse_errors": parse_errors})
            continue
        result = reconcile_action_set([action_from_case(case)], evidence)[0]
        case_results.append({
            "case_id": case["case_id"],
            "status": result.status.value,
            "provider_event_id": result.provider_event_id,
            "reasons": list(result.reasons),
            "raw_rows": len(_records_from_result(raw)),
        })
    overall = "PASS" if case_results and all(row["status"] == "PASS" for row in case_results) else "BLOCKED"
    return {"status": overall, "provider": "DATABENTO_CA", "cases": case_results}


def run_trial(*, golden_path: Path, output: Path | None = None) -> dict[str, Any]:
    env = environment_status()
    cases = load_golden_cases(golden_path)
    edi_path_text = os.getenv("EDI_CORPORATE_ACTIONS_EXPORT_PATH", "").strip()
    if edi_path_text and Path(edi_path_text).is_file():
        edi = run_edi_export_trial(golden_cases=cases, export_path=Path(edi_path_text))
    else:
        edi = {"status": "BLOCKED", "reason": "approved EDI representative-case export is missing", "cases": []}
    try:
        databento = run_databento_overlap_trial(golden_cases=cases)
    except Exception as exc:
        databento = {"status": "BLOCKED", "reason": type(exc).__name__, "cases": []}
    overall = "PASS" if edi.get("status") == "PASS" and databento.get("status") == "PASS" else "BLOCKED"
    payload = {
        "run_at": datetime.now(tz=UTC).isoformat(),
        "status": overall,
        "environment": env,
        "edi_long_history_trial": edi,
        "databento_pit_overlap_trial": databento,
        "gate": "P02-G09",
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-cases", type=Path, default=Path("tests/fixtures/data/corporate_action_provider_golden_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("CORPORATE_ACTION_PROVIDER_TRIAL_RESULTS.json"))
    args = parser.parse_args(argv)
    payload = run_trial(golden_path=args.golden_cases, output=args.output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

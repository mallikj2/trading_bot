"""Immutable experiment registry, reporting, and attribution for Phase 02B PF08.

PF08 provides provenance-first experiment records for synthetic/pre-Phase-03 runs.
It never authorizes or represents a strategy acceptance backtest. Every report carries
an explicit evidence class and immutable hashes for definition, result, and artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping

from trading_bot.data.time_utils import require_aware
from trading_bot.platform.events import canonical_json


class ExperimentContractError(ValueError):
    """Raised when an experiment definition/result violates PF08 contracts."""


class ExperimentRegistryError(RuntimeError):
    """Raised when the immutable experiment registry cannot be trusted."""


class EvidenceClass(str, Enum):
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    SIMULATION_ONLY = "SIMULATION_ONLY"
    PHASE03_ACCEPTANCE = "PHASE03_ACCEPTANCE"


_ALLOWED_PF08_EVIDENCE = {EvidenceClass.SYNTHETIC_FIXTURE, EvidenceClass.SIMULATION_ONLY}


def _hash_payload(payload: Mapping[str, Any]) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _require_sha256(value: str, field_name: str) -> str:
    text = str(value).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ExperimentContractError(f"{field_name} must be a 64-character SHA-256 hex digest")
    return text


def _decimal_map(values: Mapping[str, Decimal | str | int | float]) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for key, value in values.items():
        if not str(key).strip():
            raise ExperimentContractError("metric/attribution keys must be non-empty")
        result[str(key)] = Decimal(str(value))
    return result


def _decimal_map_to_json(values: Mapping[str, Decimal]) -> dict[str, str]:
    return {key: str(values[key]) for key in sorted(values)}


@dataclass(frozen=True, slots=True)
class ExperimentDefinition:
    name: str
    strategy_id: str
    strategy_version: str
    scenario: str
    purpose: str
    code_commit: str
    dataset_manifest_hash: str
    universe_manifest_hash: str
    parameter_manifest_hash: str
    cost_model_version: str
    acceptance_start: date
    acceptance_end: date
    random_seed: int
    definition_id: str

    def __post_init__(self) -> None:
        for field_name in ("name", "strategy_id", "strategy_version", "scenario", "purpose", "code_commit", "cost_model_version"):
            if not str(getattr(self, field_name)).strip():
                raise ExperimentContractError(f"{field_name} is required")
        if self.acceptance_end < self.acceptance_start:
            raise ExperimentContractError("acceptance_end cannot precede acceptance_start")
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int) or self.random_seed < 0:
            raise ExperimentContractError("random_seed must be a non-negative integer")
        _require_sha256(self.dataset_manifest_hash, "dataset_manifest_hash")
        _require_sha256(self.universe_manifest_hash, "universe_manifest_hash")
        _require_sha256(self.parameter_manifest_hash, "parameter_manifest_hash")
        if self.definition_id != _hash_payload(self.identity_payload()):
            raise ExperimentContractError("definition_id does not match deterministic definition content")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "scenario": self.scenario,
            "purpose": self.purpose,
            "code_commit": self.code_commit,
            "dataset_manifest_hash": self.dataset_manifest_hash,
            "universe_manifest_hash": self.universe_manifest_hash,
            "parameter_manifest_hash": self.parameter_manifest_hash,
            "cost_model_version": self.cost_model_version,
            "acceptance_start": self.acceptance_start.isoformat(),
            "acceptance_end": self.acceptance_end.isoformat(),
            "random_seed": self.random_seed,
        }

    @classmethod
    def create(cls, **kwargs: Any) -> "ExperimentDefinition":
        body = {
            "name": str(kwargs["name"]),
            "strategy_id": str(kwargs["strategy_id"]),
            "strategy_version": str(kwargs["strategy_version"]),
            "scenario": str(kwargs["scenario"]),
            "purpose": str(kwargs["purpose"]),
            "code_commit": str(kwargs["code_commit"]),
            "dataset_manifest_hash": str(kwargs["dataset_manifest_hash"]).lower(),
            "universe_manifest_hash": str(kwargs["universe_manifest_hash"]).lower(),
            "parameter_manifest_hash": str(kwargs["parameter_manifest_hash"]).lower(),
            "cost_model_version": str(kwargs["cost_model_version"]),
            "acceptance_start": kwargs["acceptance_start"].isoformat(),
            "acceptance_end": kwargs["acceptance_end"].isoformat(),
            "random_seed": int(kwargs["random_seed"]),
        }
        return cls(
            name=body["name"], strategy_id=body["strategy_id"], strategy_version=body["strategy_version"],
            scenario=body["scenario"], purpose=body["purpose"], code_commit=body["code_commit"],
            dataset_manifest_hash=body["dataset_manifest_hash"], universe_manifest_hash=body["universe_manifest_hash"],
            parameter_manifest_hash=body["parameter_manifest_hash"], cost_model_version=body["cost_model_version"],
            acceptance_start=kwargs["acceptance_start"], acceptance_end=kwargs["acceptance_end"], random_seed=body["random_seed"],
            definition_id=_hash_payload(body),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"definition_id": self.definition_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ExperimentDefinition":
        return cls(
            name=str(raw["name"]), strategy_id=str(raw["strategy_id"]), strategy_version=str(raw["strategy_version"]),
            scenario=str(raw["scenario"]), purpose=str(raw["purpose"]), code_commit=str(raw["code_commit"]),
            dataset_manifest_hash=str(raw["dataset_manifest_hash"]), universe_manifest_hash=str(raw["universe_manifest_hash"]),
            parameter_manifest_hash=str(raw["parameter_manifest_hash"]), cost_model_version=str(raw["cost_model_version"]),
            acceptance_start=date.fromisoformat(str(raw["acceptance_start"])), acceptance_end=date.fromisoformat(str(raw["acceptance_end"])),
            random_seed=int(raw["random_seed"]), definition_id=str(raw["definition_id"]),
        )


@dataclass(frozen=True, slots=True)
class PerformanceAttribution:
    long_contribution_bps: Decimal
    short_contribution_bps: Decimal
    cost_components_bps: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        normalized = _decimal_map(self.cost_components_bps)
        if any(value > 0 for value in normalized.values()):
            raise ExperimentContractError("cost attribution components must be zero or negative bps")
        object.__setattr__(self, "cost_components_bps", normalized)

    @property
    def gross_return_bps(self) -> Decimal:
        return self.long_contribution_bps + self.short_contribution_bps

    @property
    def total_cost_bps(self) -> Decimal:
        return sum(self.cost_components_bps.values(), Decimal("0"))

    @property
    def net_return_bps(self) -> Decimal:
        return self.gross_return_bps + self.total_cost_bps

    def to_dict(self) -> dict[str, Any]:
        return {
            "long_contribution_bps": str(self.long_contribution_bps),
            "short_contribution_bps": str(self.short_contribution_bps),
            "gross_return_bps": str(self.gross_return_bps),
            "cost_components_bps": _decimal_map_to_json(self.cost_components_bps),
            "total_cost_bps": str(self.total_cost_bps),
            "net_return_bps": str(self.net_return_bps),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PerformanceAttribution":
        costs = raw.get("cost_components_bps")
        if not isinstance(costs, Mapping):
            raise ExperimentContractError("cost_components_bps must be an object")
        return cls(
            long_contribution_bps=Decimal(str(raw["long_contribution_bps"])),
            short_contribution_bps=Decimal(str(raw["short_contribution_bps"])),
            cost_components_bps=_decimal_map(costs),
        )


@dataclass(frozen=True, slots=True)
class ExperimentRun:
    definition_id: str
    evidence_class: EvidenceClass
    started_at: datetime
    completed_at: datetime
    source_runtime_hash: str
    artifact_hashes: Mapping[str, str]
    metrics: Mapping[str, Decimal]
    attribution: PerformanceAttribution
    run_id: str
    result_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", require_aware(self.started_at, "started_at"))
        object.__setattr__(self, "completed_at", require_aware(self.completed_at, "completed_at"))
        if self.completed_at < self.started_at:
            raise ExperimentContractError("completed_at cannot precede started_at")
        _require_sha256(self.definition_id, "definition_id")
        _require_sha256(self.source_runtime_hash, "source_runtime_hash")
        artifacts = {str(k): _require_sha256(str(v), f"artifact_hashes[{k}]") for k, v in self.artifact_hashes.items()}
        if not artifacts:
            raise ExperimentContractError("at least one result artifact hash is required")
        object.__setattr__(self, "artifact_hashes", artifacts)
        normalized_metrics = _decimal_map(self.metrics)
        object.__setattr__(self, "metrics", normalized_metrics)
        required = {"net_return_bps", "benchmark_return_bps", "max_drawdown_bps", "sharpe", "turnover_bps"}
        missing = required - set(normalized_metrics)
        if missing:
            raise ExperimentContractError(f"missing required metrics: {sorted(missing)}")
        if normalized_metrics["net_return_bps"] != self.attribution.net_return_bps:
            raise ExperimentContractError("net_return_bps must equal attribution net return")
        if self.evidence_class == EvidenceClass.PHASE03_ACCEPTANCE:
            raise ExperimentContractError("PF08 cannot register PHASE03_ACCEPTANCE evidence")
        expected_result_hash = _hash_payload(self.result_payload())
        if self.result_hash != expected_result_hash:
            raise ExperimentContractError("result_hash does not match result payload")
        expected_run_id = _hash_payload(self.identity_payload())
        if self.run_id != expected_run_id:
            raise ExperimentContractError("run_id does not match deterministic run identity")

    def result_payload(self) -> dict[str, Any]:
        return {
            "metrics": _decimal_map_to_json(self.metrics),
            "attribution": self.attribution.to_dict(),
            "artifact_hashes": {key: self.artifact_hashes[key] for key in sorted(self.artifact_hashes)},
        }

    def identity_payload(self) -> dict[str, Any]:
        return {
            "definition_id": self.definition_id,
            "evidence_class": self.evidence_class.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "source_runtime_hash": self.source_runtime_hash,
            "result_hash": self.result_hash,
        }

    @classmethod
    def create(
        cls,
        *,
        definition_id: str,
        evidence_class: EvidenceClass,
        started_at: datetime,
        completed_at: datetime,
        source_runtime_hash: str,
        artifact_hashes: Mapping[str, str],
        metrics: Mapping[str, Decimal | str | int | float],
        attribution: PerformanceAttribution,
    ) -> "ExperimentRun":
        normalized_metrics = _decimal_map(metrics)
        artifacts = {str(k): str(v).lower() for k, v in artifact_hashes.items()}
        result_payload = {
            "metrics": _decimal_map_to_json(normalized_metrics),
            "attribution": attribution.to_dict(),
            "artifact_hashes": {key: artifacts[key] for key in sorted(artifacts)},
        }
        result_hash = _hash_payload(result_payload)
        identity = {
            "definition_id": str(definition_id).lower(),
            "evidence_class": evidence_class.value,
            "started_at": require_aware(started_at, "started_at").isoformat(),
            "completed_at": require_aware(completed_at, "completed_at").isoformat(),
            "source_runtime_hash": str(source_runtime_hash).lower(),
            "result_hash": result_hash,
        }
        return cls(
            definition_id=identity["definition_id"], evidence_class=evidence_class,
            started_at=started_at, completed_at=completed_at, source_runtime_hash=identity["source_runtime_hash"],
            artifact_hashes=artifacts, metrics=normalized_metrics, attribution=attribution,
            run_id=_hash_payload(identity), result_hash=result_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "result_hash": self.result_hash, **self.identity_payload(), **self.result_payload()}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ExperimentRun":
        attribution_raw = raw.get("attribution")
        metrics_raw = raw.get("metrics")
        artifacts_raw = raw.get("artifact_hashes")
        if not isinstance(attribution_raw, Mapping) or not isinstance(metrics_raw, Mapping) or not isinstance(artifacts_raw, Mapping):
            raise ExperimentContractError("run result objects are malformed")
        return cls(
            definition_id=str(raw["definition_id"]), evidence_class=EvidenceClass(str(raw["evidence_class"])),
            started_at=datetime.fromisoformat(str(raw["started_at"])), completed_at=datetime.fromisoformat(str(raw["completed_at"])),
            source_runtime_hash=str(raw["source_runtime_hash"]), artifact_hashes={str(k): str(v) for k, v in artifacts_raw.items()},
            metrics=_decimal_map(metrics_raw), attribution=PerformanceAttribution.from_dict(attribution_raw),
            run_id=str(raw["run_id"]), result_hash=str(raw["result_hash"]),
        )


@dataclass(frozen=True, slots=True)
class ExperimentComparison:
    baseline_run_id: str
    rows: tuple[dict[str, str], ...]
    comparison_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {"baseline_run_id": self.baseline_run_id, "rows": [dict(row) for row in self.rows], "comparison_hash": self.comparison_hash}


def compare_runs(runs: Iterable[ExperimentRun], *, baseline_run_id: str) -> ExperimentComparison:
    materialized = tuple(runs)
    by_id = {run.run_id: run for run in materialized}
    if len(by_id) != len(materialized):
        raise ExperimentContractError("duplicate run IDs in comparison")
    if baseline_run_id not in by_id:
        raise ExperimentContractError("baseline run is not present in comparison")
    baseline = by_id[baseline_run_id]
    keys = ("net_return_bps", "max_drawdown_bps", "sharpe", "turnover_bps")
    rows: list[dict[str, str]] = []
    for run in sorted(materialized, key=lambda item: item.run_id):
        row = {"run_id": run.run_id, "evidence_class": run.evidence_class.value}
        for key in keys:
            row[key] = str(run.metrics[key])
            row[f"delta_{key}"] = str(run.metrics[key] - baseline.metrics[key])
        row["total_cost_bps"] = str(run.attribution.total_cost_bps)
        row["delta_total_cost_bps"] = str(run.attribution.total_cost_bps - baseline.attribution.total_cost_bps)
        rows.append(row)
    payload = {"baseline_run_id": baseline_run_id, "rows": rows}
    return ExperimentComparison(baseline_run_id, tuple(rows), _hash_payload(payload))


class SQLiteExperimentRegistry:
    """Append-only local experiment registry with content verification."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS experiment_definitions (
                definition_id TEXT PRIMARY KEY,
                content_json TEXT NOT NULL,
                content_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiment_runs (
                run_id TEXT PRIMARY KEY,
                definition_id TEXT NOT NULL REFERENCES experiment_definitions(definition_id),
                content_json TEXT NOT NULL,
                result_hash TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS experiment_definitions_no_update BEFORE UPDATE ON experiment_definitions BEGIN SELECT RAISE(ABORT, 'experiment definitions are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS experiment_definitions_no_delete BEFORE DELETE ON experiment_definitions BEGIN SELECT RAISE(ABORT, 'experiment definitions are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS experiment_runs_no_update BEFORE UPDATE ON experiment_runs BEGIN SELECT RAISE(ABORT, 'experiment runs are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS experiment_runs_no_delete BEFORE DELETE ON experiment_runs BEGIN SELECT RAISE(ABORT, 'experiment runs are append-only'); END;
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteExperimentRegistry":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def register_definition(self, definition: ExperimentDefinition) -> bool:
        content = canonical_json(definition.to_dict())
        try:
            self._connection.execute(
                "INSERT INTO experiment_definitions(definition_id,content_json,content_hash) VALUES(?,?,?)",
                (definition.definition_id, content, sha256(content.encode("utf-8")).hexdigest()),
            )
            self._connection.commit()
            return True
        except sqlite3.IntegrityError:
            row = self._connection.execute("SELECT content_json FROM experiment_definitions WHERE definition_id=?", (definition.definition_id,)).fetchone()
            if row is None or row["content_json"] != content:
                raise ExperimentRegistryError("conflicting experiment definition content")
            return False

    def register_run(self, run: ExperimentRun) -> bool:
        definition = self._connection.execute("SELECT 1 FROM experiment_definitions WHERE definition_id=?", (run.definition_id,)).fetchone()
        if definition is None:
            raise ExperimentRegistryError("run definition must be registered first")
        content = canonical_json(run.to_dict())
        try:
            self._connection.execute(
                "INSERT INTO experiment_runs(run_id,definition_id,content_json,result_hash) VALUES(?,?,?,?)",
                (run.run_id, run.definition_id, content, run.result_hash),
            )
            self._connection.commit()
            return True
        except sqlite3.IntegrityError:
            row = self._connection.execute("SELECT content_json FROM experiment_runs WHERE run_id=?", (run.run_id,)).fetchone()
            if row is None or row["content_json"] != content:
                raise ExperimentRegistryError("conflicting experiment run content")
            return False

    def definitions(self) -> tuple[ExperimentDefinition, ...]:
        rows = self._connection.execute("SELECT content_json FROM experiment_definitions ORDER BY definition_id").fetchall()
        return tuple(ExperimentDefinition.from_dict(json.loads(row["content_json"])) for row in rows)

    def runs(self) -> tuple[ExperimentRun, ...]:
        rows = self._connection.execute("SELECT content_json FROM experiment_runs ORDER BY run_id").fetchall()
        return tuple(ExperimentRun.from_dict(json.loads(row["content_json"])) for row in rows)

    def verify(self) -> dict[str, Any]:
        definition_count = 0
        run_count = 0
        for row in self._connection.execute("SELECT * FROM experiment_definitions ORDER BY definition_id"):
            content = str(row["content_json"])
            if sha256(content.encode("utf-8")).hexdigest() != row["content_hash"]:
                raise ExperimentRegistryError("experiment definition storage hash mismatch")
            definition = ExperimentDefinition.from_dict(json.loads(content))
            if definition.definition_id != row["definition_id"]:
                raise ExperimentRegistryError("experiment definition ID mismatch")
            definition_count += 1
        for row in self._connection.execute("SELECT * FROM experiment_runs ORDER BY run_id"):
            run = ExperimentRun.from_dict(json.loads(str(row["content_json"])))
            if run.run_id != row["run_id"] or run.result_hash != row["result_hash"]:
                raise ExperimentRegistryError("experiment run storage hash mismatch")
            run_count += 1
        return {"status": "PASS", "definitions": definition_count, "runs": run_count}


def build_pf08_fixture_report(*, as_of: datetime) -> dict[str, Any]:
    """Return deterministic synthetic PF08 experiments for UI/tests only.

    Values are intentionally illustrative and must never be interpreted as evidence
    that CSMOM-LS-v0.2 is profitable or unprofitable.
    """
    moment = require_aware(as_of, "as_of")
    common = dict(
        strategy_id="CSMOM-LS",
        strategy_version="0.2",
        purpose="PF08 reporting/attribution fixture; not a Phase 03 acceptance backtest",
        code_commit="pf08-synthetic-fixture",
        dataset_manifest_hash="a" * 64,
        universe_manifest_hash="b" * 64,
        parameter_manifest_hash="c" * 64,
        cost_model_version="PF08-SYNTHETIC-v1",
        acceptance_start=date(2024, 1, 2),
        acceptance_end=date(2024, 3, 28),
        random_seed=20260808,
    )
    scenarios = [
        (
            "BASELINE_SYNTHETIC", "BASELINE",
            PerformanceAttribution(Decimal("90"), Decimal("20"), {
                "spread": Decimal("-35"), "slippage": Decimal("-25"), "regulatory": Decimal("-5"), "borrow": Decimal("-25")
            }),
            {"benchmark_return_bps": "10", "max_drawdown_bps": "-180", "sharpe": "0.25", "turnover_bps": "420"},
        ),
        (
            "COST_2X_SYNTHETIC", "COST_2X",
            PerformanceAttribution(Decimal("90"), Decimal("20"), {
                "spread": Decimal("-55"), "slippage": Decimal("-35"), "regulatory": Decimal("-10"), "borrow": Decimal("-25")
            }),
            {"benchmark_return_bps": "10", "max_drawdown_bps": "-205", "sharpe": "-0.10", "turnover_bps": "420"},
        ),
        (
            "DELAYED_EXECUTION_SYNTHETIC", "DELAYED_EXECUTION",
            PerformanceAttribution(Decimal("70"), Decimal("10"), {
                "spread": Decimal("-45"), "slippage": Decimal("-50"), "regulatory": Decimal("-5"), "borrow": Decimal("-10")
            }),
            {"benchmark_return_bps": "10", "max_drawdown_bps": "-230", "sharpe": "-0.20", "turnover_bps": "390"},
        ),
    ]
    definitions: list[ExperimentDefinition] = []
    runs: list[ExperimentRun] = []
    for index, (name, scenario, attribution, other_metrics) in enumerate(scenarios, start=1):
        definition = ExperimentDefinition.create(name=name, scenario=scenario, **common)
        run = ExperimentRun.create(
            definition_id=definition.definition_id,
            evidence_class=EvidenceClass.SYNTHETIC_FIXTURE,
            started_at=moment + (index - 1) * timedelta(minutes=1),
            completed_at=moment + (index - 1) * timedelta(minutes=1) + timedelta(seconds=30),
            source_runtime_hash=sha256(f"pf08-runtime-{scenario}".encode()).hexdigest(),
            artifact_hashes={"report_json": sha256(f"pf08-report-{scenario}".encode()).hexdigest()},
            metrics={"net_return_bps": attribution.net_return_bps, **other_metrics},
            attribution=attribution,
        )
        definitions.append(definition)
        runs.append(run)
    baseline = runs[0]
    comparison = compare_runs(runs, baseline_run_id=baseline.run_id)
    definition_by_id = {definition.definition_id: definition for definition in definitions}
    rows: list[dict[str, Any]] = []
    for run in runs:
        definition = definition_by_id[run.definition_id]
        rows.append({
            "definition": definition.to_dict(),
            "run": run.to_dict(),
            "label": "NOT_STRATEGY_EVIDENCE",
        })
    return {
        "mode": "SYNTHETIC_PF08_FIXTURE",
        "status": "PASS",
        "strategy_profitability_validated": False,
        "phase03_acceptance_backtest": False,
        "notice": "Illustrative synthetic metrics only. PF08 validates experiment lineage/reporting, not strategy performance.",
        "experiments": rows,
        "comparison": comparison.to_dict(),
    }

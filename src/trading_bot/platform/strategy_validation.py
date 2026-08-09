"""Deterministic lookahead and recursive-stability validation for Phase 02 PF05.

The validator is intentionally independent of commercial data and broker access.
It compares a strategy decision produced from the full supplied history with the
same decision produced from a history truncated at the decision date. Any
change means future rows affected an earlier result and the lookahead check
fails.

Recursive stability is tested by recomputing the same decision from multiple
approved warm-up windows. Once the frozen strategy's minimum history has been
satisfied, decision-relevant features, universe membership, rankings,
candidates, targets and optional exit decisions must remain unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

import numpy as np
import pandas as pd

from trading_bot.data.hashing import content_hash
from trading_bot.strategies.csmom_ls_v0_2 import (
    StrategyConfig,
    StrategyInputError,
    build_target_weights,
    compute_features,
    select_candidates,
)

UTC = timezone.utc


class ValidationContractError(ValueError):
    """Raised when validation inputs are incomplete or ambiguous."""


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class ValidationKind(str, Enum):
    LOOKAHEAD = "LOOKAHEAD"
    RECURSIVE = "RECURSIVE"


class DecisionSection(str, Enum):
    FEATURES = "FEATURES"
    UNIVERSE = "UNIVERSE"
    RANKING = "RANKING"
    CANDIDATES = "CANDIDATES"
    TARGETS = "TARGETS"
    EXITS = "EXITS"


JsonRecord = dict[str, Any]
ExitEvaluator = Callable[[pd.DataFrame, pd.Timestamp], Sequence[Mapping[str, Any]]]


class SnapshotEvaluator(Protocol):
    def __call__(self, frame: pd.DataFrame, decision_date: pd.Timestamp) -> "DecisionSnapshot": ...


def _normalise_scalar(value: Any, *, decimals: int = 10) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        if not np.isfinite(numeric):
            return None
        # Quantize only for comparison/reporting. Strategy calculations remain
        # untouched and use their native numeric precision.
        return format(round(numeric, decimals), f".{decimals}f")
    if pd.isna(value):
        return None
    return str(value)


def _records(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    sort_by: Sequence[str],
    decimals: int = 10,
) -> tuple[JsonRecord, ...]:
    missing = set(columns).difference(frame.columns)
    if missing:
        raise ValidationContractError(f"validation frame missing columns: {sorted(missing)}")
    selected = frame.loc[:, list(columns)].copy()
    if not selected.empty:
        selected = selected.sort_values(list(sort_by), kind="mergesort").reset_index(drop=True)
    output: list[JsonRecord] = []
    for row in selected.to_dict(orient="records"):
        output.append({key: _normalise_scalar(value, decimals=decimals) for key, value in row.items()})
    return tuple(output)


def _mapping_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    sort_keys: Sequence[str] = (),
    decimals: int = 10,
) -> tuple[JsonRecord, ...]:
    normalized = [
        {str(key): _normalise_scalar(value, decimals=decimals) for key, value in sorted(row.items())}
        for row in rows
    ]
    if sort_keys:
        normalized.sort(key=lambda row: tuple(str(row.get(key, "")) for key in sort_keys))
    else:
        normalized.sort(key=lambda row: content_hash(row))
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class DecisionSnapshot:
    decision_date: str
    features: tuple[JsonRecord, ...]
    universe: tuple[JsonRecord, ...]
    ranking: tuple[JsonRecord, ...]
    candidates: tuple[JsonRecord, ...]
    targets: tuple[JsonRecord, ...]
    exits: tuple[JsonRecord, ...] = ()

    @property
    def section_hashes(self) -> dict[str, str]:
        return {
            DecisionSection.FEATURES.value: content_hash(self.features),
            DecisionSection.UNIVERSE.value: content_hash(self.universe),
            DecisionSection.RANKING.value: content_hash(self.ranking),
            DecisionSection.CANDIDATES.value: content_hash(self.candidates),
            DecisionSection.TARGETS.value: content_hash(self.targets),
            DecisionSection.EXITS.value: content_hash(self.exits),
        }

    @property
    def state_hash(self) -> str:
        return content_hash({"decision_date": self.decision_date, "sections": self.section_hashes})

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_date": self.decision_date,
            "section_hashes": self.section_hashes,
            "state_hash": self.state_hash,
        }


@dataclass(frozen=True, slots=True)
class ValidationDifference:
    kind: ValidationKind
    decision_date: str
    section: DecisionSection
    reference_hash: str
    challenger_hash: str
    challenger_label: str

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind.value,
            "decision_date": self.decision_date,
            "section": self.section.value,
            "reference_hash": self.reference_hash,
            "challenger_hash": self.challenger_hash,
            "challenger_label": self.challenger_label,
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    kind: ValidationKind
    status: ValidationStatus
    checked_decisions: tuple[str, ...]
    comparisons: int
    differences: tuple[ValidationDifference, ...]
    configuration: Mapping[str, Any]
    generated_at: datetime

    @property
    def report_hash(self) -> str:
        return content_hash(
            {
                "kind": self.kind.value,
                "status": self.status.value,
                "checked_decisions": self.checked_decisions,
                "comparisons": self.comparisons,
                "differences": [difference.to_dict() for difference in self.differences],
                "configuration": dict(self.configuration),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "status": self.status.value,
            "checked_decisions": list(self.checked_decisions),
            "comparisons": self.comparisons,
            "difference_count": len(self.differences),
            "differences": [difference.to_dict() for difference in self.differences],
            "configuration": dict(self.configuration),
            "generated_at": self.generated_at.isoformat(),
            "report_hash": self.report_hash,
        }


_FEATURE_COLUMNS = (
    "instrument_id",
    "symbol",
    "sector",
    "price_eligibility_close",
    "adjusted_close",
    "adv60",
    "vol20",
    "sma200",
    "mom_12_1",
    "mom_6_1",
    "z_mom_12_1",
    "z_mom_6_1",
    "score",
    "base_eligible",
    "cross_section_valid",
)


def csmom_decision_snapshot(
    frame: pd.DataFrame,
    decision_date: pd.Timestamp | str | date,
    *,
    config: StrategyConfig | None = None,
    market_stress: bool = False,
    exit_evaluator: ExitEvaluator | None = None,
    numeric_decimals: int = 10,
) -> DecisionSnapshot:
    """Build the canonical PF05 decision snapshot for CSMOM-LS-v0.2."""
    cfg = config or StrategyConfig()
    target = pd.Timestamp(decision_date).normalize()
    features = compute_features(frame, cfg)
    dates = pd.to_datetime(features["session_date"]).dt.normalize()
    day = features.loc[dates.eq(target)].copy()
    if day.empty:
        raise ValidationContractError(f"no strategy observations for {target.date()}")

    candidates = select_candidates(features, target, cfg, market_stress=market_stress)
    targets = build_target_weights(candidates, features, target, cfg)

    feature_records = _records(
        day,
        _FEATURE_COLUMNS,
        sort_by=("instrument_id",),
        decimals=numeric_decimals,
    )
    universe_rows = day.loc[day["base_eligible"], ["instrument_id", "symbol", "sector"]].copy()
    universe_records = _records(
        universe_rows,
        ("instrument_id", "symbol", "sector"),
        sort_by=("instrument_id",),
        decimals=numeric_decimals,
    )

    ranking = day.loc[
        day["base_eligible"] & day["score"].notna(),
        ["instrument_id", "symbol", "sector", "score"],
    ].copy()
    if not ranking.empty:
        ranking = ranking.sort_values(
            ["score", "instrument_id"],
            ascending=[False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        ranking["rank"] = np.arange(1, len(ranking) + 1, dtype=int)
    ranking_records = _records(
        ranking,
        ("instrument_id", "symbol", "sector", "score", "rank"),
        sort_by=("rank", "instrument_id"),
        decimals=numeric_decimals,
    )

    candidate_records = _records(
        candidates,
        ("instrument_id", "symbol", "sector", "side", "score", "side_rank"),
        sort_by=("side", "side_rank", "instrument_id"),
        decimals=numeric_decimals,
    ) if not candidates.empty else ()

    target_columns = (
        "instrument_id",
        "symbol",
        "side",
        "score",
        "vol20",
        "reference_price",
        "target_weight",
    )
    target_records = _records(
        targets,
        target_columns,
        sort_by=("side", "instrument_id"),
        decimals=numeric_decimals,
    ) if not targets.empty else ()

    exits = ()
    if exit_evaluator is not None:
        exits = _mapping_records(
            exit_evaluator(frame.copy(), target),
            sort_keys=("instrument_id", "exit_reason", "exit_session"),
            decimals=numeric_decimals,
        )

    return DecisionSnapshot(
        decision_date=target.date().isoformat(),
        features=feature_records,
        universe=universe_records,
        ranking=ranking_records,
        candidates=candidate_records,
        targets=target_records,
        exits=exits,
    )


class CsmomSnapshotEvaluator:
    """Callable adapter used by generic PF05 validators."""

    def __init__(
        self,
        *,
        config: StrategyConfig | None = None,
        market_stress: bool = False,
        exit_evaluator: ExitEvaluator | None = None,
        numeric_decimals: int = 10,
    ) -> None:
        self.config = config or StrategyConfig()
        self.market_stress = market_stress
        self.exit_evaluator = exit_evaluator
        self.numeric_decimals = numeric_decimals

    def __call__(self, frame: pd.DataFrame, decision_date: pd.Timestamp) -> DecisionSnapshot:
        return csmom_decision_snapshot(
            frame,
            decision_date,
            config=self.config,
            market_stress=self.market_stress,
            exit_evaluator=self.exit_evaluator,
            numeric_decimals=self.numeric_decimals,
        )


def _compare(
    reference: DecisionSnapshot,
    challenger: DecisionSnapshot,
    *,
    kind: ValidationKind,
    challenger_label: str,
) -> tuple[ValidationDifference, ...]:
    if reference.decision_date != challenger.decision_date:
        raise ValidationContractError("cannot compare snapshots from different decision dates")
    differences: list[ValidationDifference] = []
    ref_hashes = reference.section_hashes
    alt_hashes = challenger.section_hashes
    for section in DecisionSection:
        if ref_hashes[section.value] != alt_hashes[section.value]:
            differences.append(
                ValidationDifference(
                    kind=kind,
                    decision_date=reference.decision_date,
                    section=section,
                    reference_hash=ref_hashes[section.value],
                    challenger_hash=alt_hashes[section.value],
                    challenger_label=challenger_label,
                )
            )
    return tuple(differences)


def _normalise_decision_dates(
    frame: pd.DataFrame,
    decision_dates: Iterable[pd.Timestamp | str | date],
) -> tuple[pd.Timestamp, ...]:
    if "session_date" not in frame.columns:
        raise ValidationContractError("frame must contain session_date")
    available = set(pd.to_datetime(frame["session_date"]).dt.normalize())
    values: list[pd.Timestamp] = []
    for raw in decision_dates:
        value = pd.Timestamp(raw).normalize()
        if value not in available:
            raise ValidationContractError(f"decision date {value.date()} is absent from input")
        values.append(value)
    unique = tuple(sorted(set(values)))
    if not unique:
        raise ValidationContractError("at least one decision date is required")
    return unique


def validate_lookahead(
    frame: pd.DataFrame,
    *,
    decision_dates: Iterable[pd.Timestamp | str | date],
    evaluator: SnapshotEvaluator | None = None,
    generated_at: datetime | None = None,
) -> ValidationReport:
    """Fail if future rows alter any earlier decision section."""
    eval_fn = evaluator or CsmomSnapshotEvaluator()
    decisions = _normalise_decision_dates(frame, decision_dates)
    dates = pd.to_datetime(frame["session_date"]).dt.normalize()
    differences: list[ValidationDifference] = []
    comparisons = 0

    for decision in decisions:
        reference = eval_fn(frame.copy(), decision)
        truncated = frame.loc[dates.le(decision)].copy()
        challenger = eval_fn(truncated, decision)
        comparisons += 1
        differences.extend(
            _compare(
                reference,
                challenger,
                kind=ValidationKind.LOOKAHEAD,
                challenger_label="TRUNCATED_AT_DECISION",
            )
        )

    status = ValidationStatus.PASS if not differences else ValidationStatus.FAIL
    return ValidationReport(
        kind=ValidationKind.LOOKAHEAD,
        status=status,
        checked_decisions=tuple(value.date().isoformat() for value in decisions),
        comparisons=comparisons,
        differences=tuple(differences),
        configuration={"method": "FULL_VS_TRUNCATED_AT_DECISION"},
        generated_at=(generated_at or datetime.now(tz=UTC)),
    )


def validate_recursive_stability(
    frame: pd.DataFrame,
    *,
    decision_dates: Iterable[pd.Timestamp | str | date],
    warmup_sessions: Sequence[int] = (300, 320, 360),
    evaluator: SnapshotEvaluator | None = None,
    minimum_approved_history: int = 300,
    generated_at: datetime | None = None,
) -> ValidationReport:
    """Fail if approved warm-up lengths change the same historical decision."""
    if not warmup_sessions:
        raise ValidationContractError("warmup_sessions cannot be empty")
    if minimum_approved_history < 1:
        raise ValidationContractError("minimum_approved_history must be positive")
    values = tuple(sorted(set(int(value) for value in warmup_sessions)))
    if any(value < minimum_approved_history for value in values):
        raise ValidationContractError(
            f"all warmup windows must be >= {minimum_approved_history} sessions"
        )

    eval_fn = evaluator or CsmomSnapshotEvaluator()
    decisions = _normalise_decision_dates(frame, decision_dates)
    all_dates = pd.to_datetime(frame["session_date"]).dt.normalize()
    differences: list[ValidationDifference] = []
    comparisons = 0

    for decision in decisions:
        historical_dates = sorted(set(all_dates[all_dates.le(decision)]))
        max_required = max(values)
        if len(historical_dates) < max_required:
            raise ValidationContractError(
                f"decision {decision.date()} has {len(historical_dates)} sessions; "
                f"{max_required} required for recursive validation"
            )
        full_history = frame.loc[all_dates.le(decision)].copy()
        reference = eval_fn(full_history, decision)
        for warmup in values:
            keep = set(historical_dates[-warmup:])
            challenger_frame = frame.loc[all_dates.isin(keep)].copy()
            challenger = eval_fn(challenger_frame, decision)
            comparisons += 1
            differences.extend(
                _compare(
                    reference,
                    challenger,
                    kind=ValidationKind.RECURSIVE,
                    challenger_label=f"LAST_{warmup}_SESSIONS",
                )
            )

    status = ValidationStatus.PASS if not differences else ValidationStatus.FAIL
    return ValidationReport(
        kind=ValidationKind.RECURSIVE,
        status=status,
        checked_decisions=tuple(value.date().isoformat() for value in decisions),
        comparisons=comparisons,
        differences=tuple(differences),
        configuration={
            "method": "FULL_TRUNCATED_HISTORY_VS_WARMUP_WINDOWS",
            "warmup_sessions": list(values),
            "minimum_approved_history": minimum_approved_history,
        },
        generated_at=(generated_at or datetime.now(tz=UTC)),
    )


def validate_strategy_bias_suite(
    frame: pd.DataFrame,
    *,
    decision_dates: Iterable[pd.Timestamp | str | date],
    warmup_sessions: Sequence[int] = (300, 320, 360),
    evaluator: SnapshotEvaluator | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Run both mandatory PF05 analyses and return one deterministic summary."""
    at = generated_at or datetime.now(tz=UTC)
    lookahead = validate_lookahead(
        frame,
        decision_dates=decision_dates,
        evaluator=evaluator,
        generated_at=at,
    )
    recursive = validate_recursive_stability(
        frame,
        decision_dates=decision_dates,
        warmup_sessions=warmup_sessions,
        evaluator=evaluator,
        generated_at=at,
    )
    overall = ValidationStatus.PASS if (
        lookahead.status is ValidationStatus.PASS
        and recursive.status is ValidationStatus.PASS
    ) else ValidationStatus.FAIL
    result = {
        "strategy_id": "CSMOM-LS-v0.2",
        "status": overall.value,
        "lookahead": lookahead.to_dict(),
        "recursive": recursive.to_dict(),
    }
    result["suite_hash"] = content_hash(result)
    return result

"""Deterministic research reference for CSMOM-LS-v0.2.

The module implements the frozen Phase 01 strategy-level contract:

* point-in-time momentum and liquidity features;
* deterministic candidate ranking;
* matched long/short target weights;
* deterministic whole-share feasibility allocation;
* decision and target-expiry timestamps.

It does not connect to a broker, simulate fills, manage live risk, or authorize
orders. Those responsibilities belong to later project phases.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Final, Mapping
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml


STRATEGY_ID: Final[str] = "CSMOM-LS-v0.2"
NEW_YORK: Final[ZoneInfo] = ZoneInfo("America/New_York")

REQUIRED_COLUMNS: Final[set[str]] = {
    "session_date",
    "instrument_id",
    "symbol",
    "raw_close",
    "adjusted_close",
    "raw_volume",
    "market_cap",
    "exchange",
    "security_type",
    "sector",
    "data_quality_status",
}


class StrategyInputError(ValueError):
    """Raised when data violate the frozen strategy contract."""


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str = STRATEGY_ID
    min_price: float = 10.0
    min_market_cap: float = 2_000_000_000.0
    min_adv60: float = 25_000_000.0
    min_valid_sessions: int = 300
    max_annualized_volatility: float = 0.80
    score_threshold: float = 0.75
    max_longs: int = 3
    max_shorts: int = 3
    max_names_per_sector_per_side: int = 2
    min_cross_section: int = 20
    mom_12_1_weight: float = 0.60
    mom_6_1_weight: float = 0.40
    target_side_gross: float = 0.50
    max_single_name_weight: float = 0.20
    max_absolute_net_exposure: float = 0.10
    decision_delay_minutes: int = 30
    execution_start: str = "10:00"
    execution_end: str = "10:30"

    def __post_init__(self) -> None:
        if self.strategy_id != STRATEGY_ID:
            raise ValueError(f"strategy_id must be {STRATEGY_ID}")
        positive_fields = {
            "min_price": self.min_price,
            "min_market_cap": self.min_market_cap,
            "min_adv60": self.min_adv60,
            "max_annualized_volatility": self.max_annualized_volatility,
            "score_threshold": self.score_threshold,
            "target_side_gross": self.target_side_gross,
            "max_single_name_weight": self.max_single_name_weight,
        }
        for name, value in positive_fields.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.min_valid_sessions < 252:
            raise ValueError("min_valid_sessions must be at least 252")
        if self.min_cross_section < 2:
            raise ValueError("min_cross_section must be at least 2")
        if self.max_longs < 0 or self.max_shorts < 0:
            raise ValueError("position counts cannot be negative")
        if self.max_names_per_sector_per_side < 1:
            raise ValueError("max_names_per_sector_per_side must be at least 1")
        if not np.isclose(self.mom_12_1_weight + self.mom_6_1_weight, 1.0):
            raise ValueError("momentum weights must sum to 1.0")
        if self.target_side_gross > 0.50:
            raise ValueError("target_side_gross cannot exceed 0.50 in Phase 01")
        if not 0 <= self.max_absolute_net_exposure <= 1:
            raise ValueError("max_absolute_net_exposure must be in [0, 1]")
        if self.decision_delay_minutes < 0:
            raise ValueError("decision_delay_minutes cannot be negative")
        _parse_clock(self.execution_start)
        _parse_clock(self.execution_end)
        if _parse_clock(self.execution_end) <= _parse_clock(self.execution_start):
            raise ValueError("execution_end must be later than execution_start")


def _parse_clock(value: str) -> time:
    try:
        hour, minute = (int(part) for part in value.split(":"))
        return time(hour=hour, minute=minute)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid HH:MM clock value: {value!r}") from exc


def load_strategy_config(path: str | Path) -> StrategyConfig:
    """Load the canonical YAML and reject unknown or missing runtime keys."""
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise StrategyInputError("strategy configuration must be a mapping")

    runtime = payload.get("runtime")
    if not isinstance(runtime, Mapping):
        raise StrategyInputError("configuration must contain a runtime mapping")

    allowed = {field.name for field in fields(StrategyConfig)}
    unknown = set(runtime) - allowed
    missing = allowed - set(runtime)
    if unknown:
        raise StrategyInputError(f"unknown runtime configuration keys: {sorted(unknown)}")
    if missing:
        raise StrategyInputError(f"missing runtime configuration keys: {sorted(missing)}")
    return StrategyConfig(**dict(runtime))


def _validate_input(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise StrategyInputError(f"missing required columns: {sorted(missing)}")

    data = frame.copy()
    data["session_date"] = pd.to_datetime(data["session_date"], errors="raise").dt.normalize()
    for column in ("instrument_id", "symbol", "exchange", "security_type", "sector"):
        data[column] = data[column].astype(str).str.strip()
        if data[column].eq("").any():
            raise StrategyInputError(f"{column} cannot be blank")

    duplicate_mask = data.duplicated(["session_date", "instrument_id"], keep=False)
    if duplicate_mask.any():
        sample = data.loc[duplicate_mask, ["session_date", "instrument_id"]].head(5)
        raise StrategyInputError(
            "duplicate (session_date, instrument_id) rows detected: "
            f"{sample.to_dict(orient='records')}"
        )

    numeric_columns = ["raw_close", "adjusted_close", "raw_volume", "market_cap"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if data[numeric_columns].isna().any().any():
        raise StrategyInputError("required numeric fields contain null or non-numeric values")
    if (~np.isfinite(data[numeric_columns].to_numpy(dtype=float))).any():
        raise StrategyInputError("required numeric fields contain non-finite values")
    if (data[["raw_close", "adjusted_close", "market_cap"]] <= 0).any().any():
        raise StrategyInputError("prices and market_cap must be positive")
    if (data["raw_volume"] < 0).any():
        raise StrategyInputError("raw_volume cannot be negative")

    allowed_exchanges = {"NYSE", "NASDAQ"}
    bad_exchanges = set(data["exchange"]) - allowed_exchanges
    if bad_exchanges:
        raise StrategyInputError(f"unsupported exchanges: {sorted(bad_exchanges)}")
    bad_quality = set(data["data_quality_status"]) - {"VALID", "SUSPECT", "REJECTED"}
    if bad_quality:
        raise StrategyInputError(f"unsupported data quality states: {sorted(bad_quality)}")

    if "entry_blocked" not in data.columns:
        data["entry_blocked"] = False
    data["entry_blocked"] = data["entry_blocked"].astype(bool)

    return data.sort_values(
        ["instrument_id", "session_date"], kind="mergesort"
    ).reset_index(drop=True)


def _robust_zscore(series: pd.Series) -> pd.Series:
    """Return a 2.5%/97.5% winsorized median/MAD z-score."""
    valid = series.dropna()
    result = pd.Series(np.nan, index=series.index, dtype=float)
    if valid.empty:
        return result
    clipped = valid.clip(lower=valid.quantile(0.025), upper=valid.quantile(0.975))
    median = float(clipped.median())
    mad = float((clipped - median).abs().median())
    scale = 1.4826 * mad
    if not np.isfinite(scale) or scale <= 0:
        return result
    result.loc[clipped.index] = (clipped - median) / scale
    return result


def compute_features(
    frame: pd.DataFrame,
    config: StrategyConfig | None = None,
) -> pd.DataFrame:
    """Compute point-in-time features using only current and prior rows."""
    cfg = config or StrategyConfig()
    data = _validate_input(frame)
    grouped = data.groupby("instrument_id", sort=False, group_keys=False)

    data["valid_session_count"] = grouped.cumcount() + 1
    # Raw close * raw volume is split invariant when the source records the
    # corresponding post-split price and volume. Adjusted close is not used.
    data["raw_dollar_volume"] = data["raw_close"] * data["raw_volume"]
    data["adv60"] = grouped["raw_dollar_volume"].transform(
        lambda s: s.rolling(60, min_periods=60).median()
    )
    data["log_return"] = grouped["adjusted_close"].transform(
        lambda s: np.log(s / s.shift(1))
    )
    data["vol20"] = grouped["log_return"].transform(
        lambda s: s.rolling(20, min_periods=20).std(ddof=1) * np.sqrt(252.0)
    )
    data["sma200"] = grouped["adjusted_close"].transform(
        lambda s: s.rolling(200, min_periods=200).mean()
    )

    close_m21 = grouped["adjusted_close"].shift(21)
    close_m126 = grouped["adjusted_close"].shift(126)
    close_m252 = grouped["adjusted_close"].shift(252)
    data["mom_12_1"] = np.log(close_m21 / close_m252)
    data["mom_6_1"] = np.log(close_m21 / close_m126)

    data["base_eligible"] = (
        data["exchange"].isin(["NYSE", "NASDAQ"])
        & data["security_type"].eq("COMMON_STOCK")
        & data["data_quality_status"].eq("VALID")
        & ~data["entry_blocked"]
        & data["adjusted_close"].ge(cfg.min_price)
        & data["market_cap"].ge(cfg.min_market_cap)
        & data["adv60"].ge(cfg.min_adv60)
        & data["valid_session_count"].ge(cfg.min_valid_sessions)
        & data["vol20"].le(cfg.max_annualized_volatility)
        & data[["mom_12_1", "mom_6_1", "sma200"]].notna().all(axis=1)
    )

    scored: list[pd.DataFrame] = []
    for _, day in data.groupby("session_date", sort=True):
        day = day.copy()
        eligible_idx = day.index[day["base_eligible"]]
        day["z_mom_12_1"] = np.nan
        day["z_mom_6_1"] = np.nan
        day["score"] = np.nan
        day["cross_section_valid"] = len(eligible_idx) >= cfg.min_cross_section
        if day["cross_section_valid"].iloc[0]:
            z12 = _robust_zscore(day.loc[eligible_idx, "mom_12_1"])
            z6 = _robust_zscore(day.loc[eligible_idx, "mom_6_1"])
            day.loc[eligible_idx, "z_mom_12_1"] = z12
            day.loc[eligible_idx, "z_mom_6_1"] = z6
            day.loc[eligible_idx, "score"] = (
                cfg.mom_12_1_weight * z12 + cfg.mom_6_1_weight * z6
            )
        scored.append(day)

    result = pd.concat(scored, ignore_index=True) if scored else data.copy()
    return result.sort_values(
        ["session_date", "instrument_id"], kind="mergesort"
    ).reset_index(drop=True)


def select_candidates(
    feature_frame: pd.DataFrame,
    decision_date: str | date | pd.Timestamp,
    config: StrategyConfig | None = None,
    *,
    market_stress: bool = False,
) -> pd.DataFrame:
    """Select deterministic long and short research candidates."""
    cfg = config or StrategyConfig()
    columns = ["session_date", "instrument_id", "symbol", "sector", "side", "score", "side_rank"]
    if market_stress:
        return pd.DataFrame(columns=columns)

    required = {
        "session_date",
        "instrument_id",
        "symbol",
        "sector",
        "adjusted_close",
        "sma200",
        "mom_12_1",
        "mom_6_1",
        "score",
        "base_eligible",
        "cross_section_valid",
    }
    missing = required.difference(feature_frame.columns)
    if missing:
        raise StrategyInputError(f"feature frame missing columns: {sorted(missing)}")

    target_date = pd.Timestamp(decision_date).normalize()
    dates = pd.to_datetime(feature_frame["session_date"]).dt.normalize()
    day = feature_frame.loc[dates.eq(target_date)].copy()
    if day.empty:
        raise StrategyInputError(f"no observations for decision date {target_date.date()}")
    if not bool(day["cross_section_valid"].all()):
        return pd.DataFrame(columns=columns)

    common = day["base_eligible"] & day["score"].notna()
    long_mask = (
        common
        & day["score"].ge(cfg.score_threshold)
        & day["mom_12_1"].gt(0)
        & day["mom_6_1"].gt(0)
        & day["adjusted_close"].gt(day["sma200"])
    )
    short_mask = (
        common
        & day["score"].le(-cfg.score_threshold)
        & day["mom_12_1"].lt(0)
        & day["mom_6_1"].lt(0)
        & day["adjusted_close"].lt(day["sma200"])
    )

    def select_side(mask: pd.Series, side: str, limit: int, ascending: bool) -> pd.DataFrame:
        ranked = day.loc[
            mask, ["session_date", "instrument_id", "symbol", "sector", "score"]
        ].sort_values(
            ["score", "instrument_id"], ascending=[ascending, True], kind="mergesort"
        )
        selected_rows: list[pd.Series] = []
        sector_counts: dict[str, int] = {}
        for _, row in ranked.iterrows():
            sector = str(row["sector"])
            if sector_counts.get(sector, 0) >= cfg.max_names_per_sector_per_side:
                continue
            selected_rows.append(row)
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            if len(selected_rows) >= limit:
                break
        if not selected_rows:
            return ranked.head(0).assign(side=side)
        return pd.DataFrame(selected_rows).assign(side=side)

    longs = select_side(long_mask, "LONG", cfg.max_longs, ascending=False)
    shorts = select_side(short_mask, "SHORT", cfg.max_shorts, ascending=True)
    longs["side_rank"] = np.arange(1, len(longs) + 1, dtype=int)
    shorts["side_rank"] = np.arange(1, len(shorts) + 1, dtype=int)
    output = pd.concat([longs, shorts], ignore_index=True)
    if output.empty:
        return pd.DataFrame(columns=columns)
    return output[columns].reset_index(drop=True)


def _capped_normalized_weights(
    inverse_volatility: pd.Series,
    side_gross: float,
    cap: float,
) -> pd.Series:
    """Allocate side gross deterministically under a per-name cap."""
    if side_gross <= 0 or inverse_volatility.empty:
        return pd.Series(dtype=float, index=inverse_volatility.index)
    weights = pd.Series(0.0, index=inverse_volatility.index)
    remaining = list(inverse_volatility.sort_index().index)
    residual = side_gross
    while remaining and residual > 1e-12:
        raw = inverse_volatility.loc[remaining]
        proposal = residual * raw / raw.sum()
        capped_now = proposal[proposal > cap + 1e-12]
        if capped_now.empty:
            weights.loc[remaining] = proposal
            residual = 0.0
        else:
            for idx in sorted(capped_now.index):
                weights.loc[idx] = cap
                residual -= cap
                remaining.remove(idx)
    return weights


def build_target_weights(
    candidates: pd.DataFrame,
    feature_frame: pd.DataFrame,
    decision_date: str | date | pd.Timestamp,
    config: StrategyConfig | None = None,
) -> pd.DataFrame:
    """Build matched-side inverse-volatility targets.

    If either side has no candidate, the function returns no target. When sides
    have unequal capacity, both sides are scaled to the smaller feasible gross,
    preventing unintended directional exposure.
    """
    cfg = config or StrategyConfig()
    columns = [
        "session_date",
        "instrument_id",
        "symbol",
        "side",
        "score",
        "vol20",
        "reference_price",
        "target_weight",
    ]
    if candidates.empty:
        return pd.DataFrame(columns=columns)

    target_date = pd.Timestamp(decision_date).normalize()
    day = feature_frame.loc[
        pd.to_datetime(feature_frame["session_date"]).dt.normalize().eq(target_date),
        ["instrument_id", "vol20", "adjusted_close"],
    ].copy()
    merged = candidates.merge(day, on="instrument_id", how="left", validate="one_to_one")
    if merged[["vol20", "adjusted_close"]].isna().any().any():
        raise StrategyInputError("candidate feature values are missing")

    counts = merged.groupby("side")["instrument_id"].count().to_dict()
    if counts.get("LONG", 0) == 0 or counts.get("SHORT", 0) == 0:
        return pd.DataFrame(columns=columns)

    feasible_side_gross = min(
        cfg.target_side_gross,
        counts["LONG"] * cfg.max_single_name_weight,
        counts["SHORT"] * cfg.max_single_name_weight,
    )
    if feasible_side_gross <= 0:
        return pd.DataFrame(columns=columns)

    merged["target_weight"] = 0.0
    for side, sign in (("LONG", 1.0), ("SHORT", -1.0)):
        idx = merged.index[merged["side"].eq(side)]
        inverse_vol = 1.0 / merged.loc[idx, "vol20"].clip(lower=0.10)
        abs_weights = _capped_normalized_weights(
            inverse_volatility=inverse_vol,
            side_gross=feasible_side_gross,
            cap=cfg.max_single_name_weight,
        )
        merged.loc[idx, "target_weight"] = sign * abs_weights

    merged = merged.rename(columns={"adjusted_close": "reference_price"})
    return merged[columns].sort_values(
        ["side", "target_weight", "instrument_id"],
        ascending=[True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def allocate_whole_shares(
    targets: pd.DataFrame,
    equity: float,
    config: StrategyConfig | None = None,
) -> pd.DataFrame:
    """Create a deterministic no-addition whole-share feasibility allocation."""
    cfg = config or StrategyConfig()
    if equity <= 0:
        raise ValueError("equity must be positive")
    required = {"instrument_id", "side", "reference_price", "target_weight"}
    missing = required.difference(targets.columns)
    if missing:
        raise StrategyInputError(f"targets missing columns: {sorted(missing)}")

    result = targets.copy()
    if result.empty:
        result["shares"] = pd.Series(dtype=int)
        result["signed_market_value"] = pd.Series(dtype=float)
        result["allocation_valid"] = pd.Series(dtype=bool)
        return result

    if (result["reference_price"] <= 0).any():
        raise StrategyInputError("reference_price must be positive")
    result["shares"] = np.floor(
        result["target_weight"].abs() * equity / result["reference_price"]
    ).astype(int)
    sign = np.where(result["side"].eq("LONG"), 1.0, -1.0)
    result["signed_market_value"] = sign * result["shares"] * result["reference_price"]

    max_net_value = cfg.max_absolute_net_exposure * equity
    # Remove shares only from the larger side until the net constraint holds.
    while abs(float(result["signed_market_value"].sum())) > max_net_value + 1e-9:
        net = float(result["signed_market_value"].sum())
        side_to_reduce = "LONG" if net > 0 else "SHORT"
        eligible = result.index[(result["side"] == side_to_reduce) & (result["shares"] > 0)]
        if len(eligible) == 0:
            break

        choices: list[tuple[float, str, int]] = []
        for idx in eligible:
            reduction = result.at[idx, "reference_price"] * (1.0 if side_to_reduce == "LONG" else -1.0)
            new_net = net - reduction
            choices.append((abs(new_net), str(result.at[idx, "instrument_id"]), int(idx)))
        _, _, chosen = min(choices)
        result.at[chosen, "shares"] -= 1
        result.at[chosen, "signed_market_value"] = (
            (1.0 if result.at[chosen, "side"] == "LONG" else -1.0)
            * result.at[chosen, "shares"]
            * result.at[chosen, "reference_price"]
        )

    long_value = float(result.loc[result["side"].eq("LONG"), "signed_market_value"].sum())
    short_value = abs(float(result.loc[result["side"].eq("SHORT"), "signed_market_value"].sum()))
    net_value = float(result["signed_market_value"].sum())
    valid = long_value > 0 and short_value > 0 and abs(net_value) <= max_net_value + 1e-9
    result["allocation_valid"] = valid
    return result.reset_index(drop=True)


def decision_timestamp_from_close(
    official_session_close: datetime | pd.Timestamp,
    config: StrategyConfig | None = None,
) -> pd.Timestamp:
    """Return official close plus the configured data-finality delay."""
    cfg = config or StrategyConfig()
    close = pd.Timestamp(official_session_close)
    if close.tzinfo is None:
        raise StrategyInputError("official_session_close must be timezone-aware")
    close = close.tz_convert(NEW_YORK)
    return close + pd.Timedelta(minutes=cfg.decision_delay_minutes)


def build_target_records(
    targets: pd.DataFrame,
    official_session_close: datetime | pd.Timestamp,
    next_session_date: str | date | pd.Timestamp,
    config: StrategyConfig | None = None,
) -> pd.DataFrame:
    """Stamp target weights with deterministic decision and expiry times."""
    cfg = config or StrategyConfig()
    if targets.empty:
        return targets.assign(
            strategy_id=pd.Series(dtype=str),
            decision_timestamp=pd.Series(dtype="datetime64[ns, America/New_York]"),
            execution_start=pd.Series(dtype="datetime64[ns, America/New_York]"),
            expires_at=pd.Series(dtype="datetime64[ns, America/New_York]"),
        )

    session = pd.Timestamp(next_session_date).date()
    start_clock = _parse_clock(cfg.execution_start)
    end_clock = _parse_clock(cfg.execution_end)
    execution_start = pd.Timestamp(datetime.combine(session, start_clock), tz=NEW_YORK)
    expires_at = pd.Timestamp(datetime.combine(session, end_clock), tz=NEW_YORK)
    decision_ts = decision_timestamp_from_close(official_session_close, cfg)
    if execution_start <= decision_ts:
        raise StrategyInputError("next-session execution window must follow decision timestamp")

    records = targets.copy()
    records["strategy_id"] = cfg.strategy_id
    records["decision_timestamp"] = decision_ts
    records["execution_start"] = execution_start
    records["expires_at"] = expires_at
    return records


def generate_targets(
    frame: pd.DataFrame,
    decision_date: str | date | pd.Timestamp,
    config: StrategyConfig | None = None,
    *,
    market_stress: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convenience pipeline returning features, candidates, and target weights."""
    cfg = config or StrategyConfig()
    features = compute_features(frame, cfg)
    candidates = select_candidates(features, decision_date, cfg, market_stress=market_stress)
    targets = build_target_weights(candidates, features, decision_date, cfg)
    return features, candidates, targets

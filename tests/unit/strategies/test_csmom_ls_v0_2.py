from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from trading_bot.strategies.csmom_ls_v0_2 import (
    STRATEGY_ID,
    StrategyConfig,
    StrategyInputError,
    allocate_whole_shares,
    build_target_records,
    build_target_weights,
    compute_features,
    decision_timestamp_from_close,
    generate_targets,
    load_strategy_config,
    select_candidates,
)


NY = ZoneInfo("America/New_York")


def make_panel(
    symbols: int = 24,
    sessions: int = 330,
    start: str = "2024-01-02",
    *,
    identical: bool = False,
) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=sessions)
    rows: list[dict[str, object]] = []
    slopes = np.zeros(symbols) if identical else np.linspace(-0.0015, 0.0015, symbols)
    for idx, slope in enumerate(slopes):
        instrument_id = f"ID{idx:03d}"
        symbol = f"S{idx:02d}"
        # Small oscillation prevents zero volatility without changing rank order.
        t = np.arange(sessions)
        phase = 0.0 if identical else float(idx)
        adjusted = 100.0 * np.exp(t * slope + 0.002 * np.sin(t / 11.0 + phase))
        raw = adjusted.copy()
        for session_date, raw_close, adjusted_close in zip(dates, raw, adjusted, strict=True):
            rows.append(
                {
                    "session_date": session_date,
                    "instrument_id": instrument_id,
                    "symbol": symbol,
                    "raw_close": float(raw_close),
                    "adjusted_close": float(adjusted_close),
                    "raw_volume": 1_000_000.0,
                    "market_cap": 5_000_000_000.0,
                    "exchange": "NYSE" if idx % 2 == 0 else "NASDAQ",
                    "security_type": "COMMON_STOCK",
                    "sector": f"SECTOR{idx % 6}",
                    "data_quality_status": "VALID",
                    "entry_blocked": False,
                }
            )
    return pd.DataFrame(rows)


def test_yaml_runtime_matches_dataclass() -> None:
    path = Path(__file__).parents[3] / "configs" / "strategies" / "csmom_ls_v0_2.yaml"
    config = load_strategy_config(path)
    assert config.strategy_id == STRATEGY_ID
    assert config.score_threshold == 0.75
    assert config.execution_end == "10:30"


def test_missing_required_column_is_rejected() -> None:
    with pytest.raises(StrategyInputError, match="missing required columns"):
        compute_features(make_panel().drop(columns="raw_volume"))


def test_duplicate_stable_instrument_key_is_rejected() -> None:
    frame = make_panel()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(StrategyInputError, match="duplicate"):
        compute_features(frame)


def test_exact_momentum_formula() -> None:
    frame = make_panel()
    features = compute_features(frame)
    instrument = features.loc[features["instrument_id"].eq("ID023")].reset_index(drop=True)
    row = instrument.iloc[-1]
    expected_12_1 = np.log(instrument.iloc[-22]["adjusted_close"] / instrument.iloc[-253]["adjusted_close"])
    expected_6_1 = np.log(instrument.iloc[-22]["adjusted_close"] / instrument.iloc[-127]["adjusted_close"])
    assert row["mom_12_1"] == pytest.approx(expected_12_1)
    assert row["mom_6_1"] == pytest.approx(expected_6_1)


def test_non_vacuous_candidate_generation_selects_three_each_side() -> None:
    frame = make_panel()
    features, candidates, targets = generate_targets(frame, frame["session_date"].max())
    day = features.loc[features["session_date"].eq(frame["session_date"].max())]
    assert int(day["base_eligible"].sum()) == 24
    assert (candidates["side"] == "LONG").sum() == 3
    assert (candidates["side"] == "SHORT").sum() == 3
    assert len(targets) == 6


def test_selected_candidates_satisfy_sign_and_trend_rules() -> None:
    frame = make_panel()
    features, candidates, _ = generate_targets(frame, frame["session_date"].max())
    day = features.loc[features["session_date"].eq(frame["session_date"].max())]
    merged = candidates.merge(day, on=["session_date", "instrument_id", "symbol", "sector"])
    longs = merged.loc[merged["side"].eq("LONG")]
    shorts = merged.loc[merged["side"].eq("SHORT")]
    assert not longs.empty and not shorts.empty
    assert (longs["score_x"] >= 0.75).all()
    assert (longs["mom_12_1"] > 0).all()
    assert (longs["mom_6_1"] > 0).all()
    assert (longs["adjusted_close"] > longs["sma200"]).all()
    assert (shorts["score_x"] <= -0.75).all()
    assert (shorts["mom_12_1"] < 0).all()
    assert (shorts["mom_6_1"] < 0).all()
    assert (shorts["adjusted_close"] < shorts["sma200"]).all()


def test_short_order_is_most_negative_first() -> None:
    frame = make_panel()
    _, candidates, _ = generate_targets(frame, frame["session_date"].max())
    shorts = candidates.loc[candidates["side"].eq("SHORT")]
    assert shorts["score"].is_monotonic_increasing
    assert shorts["side_rank"].tolist() == [1, 2, 3]


def test_threshold_boundary_is_inclusive_and_ties_use_instrument_id() -> None:
    date = pd.Timestamp("2026-01-05")
    manual = pd.DataFrame(
        [
            dict(session_date=date, instrument_id="B", symbol="B", sector="X", adjusted_close=120.0, sma200=100.0, mom_12_1=0.2, mom_6_1=0.1, score=0.75, base_eligible=True, cross_section_valid=True),
            dict(session_date=date, instrument_id="A", symbol="A", sector="X", adjusted_close=120.0, sma200=100.0, mom_12_1=0.2, mom_6_1=0.1, score=0.75, base_eligible=True, cross_section_valid=True),
            dict(session_date=date, instrument_id="D", symbol="D", sector="Y", adjusted_close=80.0, sma200=100.0, mom_12_1=-0.2, mom_6_1=-0.1, score=-0.75, base_eligible=True, cross_section_valid=True),
            dict(session_date=date, instrument_id="C", symbol="C", sector="Y", adjusted_close=80.0, sma200=100.0, mom_12_1=-0.2, mom_6_1=-0.1, score=-0.75, base_eligible=True, cross_section_valid=True),
        ]
    )
    config = StrategyConfig(min_cross_section=2, max_longs=2, max_shorts=2)
    selected = select_candidates(manual, date, config)
    assert selected.loc[selected["side"].eq("LONG"), "instrument_id"].tolist() == ["A", "B"]
    assert selected.loc[selected["side"].eq("SHORT"), "instrument_id"].tolist() == ["C", "D"]


def test_zero_mad_fails_closed() -> None:
    frame = make_panel(identical=True)
    features = compute_features(frame)
    day = features.loc[features["session_date"].eq(frame["session_date"].max())]
    assert day["score"].isna().all()
    assert select_candidates(features, frame["session_date"].max()).empty


def test_future_rows_do_not_change_past_targets() -> None:
    frame = make_panel()
    decision_date = frame["session_date"].max()
    _, candidates_before, targets_before = generate_targets(frame, decision_date)

    future = frame.loc[frame["session_date"].eq(decision_date)].copy()
    future["session_date"] = pd.Timestamp(decision_date) + pd.offsets.BDay(1)
    future["adjusted_close"] *= np.linspace(0.25, 4.0, len(future))
    future["raw_close"] = future["adjusted_close"]
    extended = pd.concat([frame, future], ignore_index=True)
    _, candidates_after, targets_after = generate_targets(extended, decision_date)
    pd.testing.assert_frame_equal(candidates_before, candidates_after)
    pd.testing.assert_frame_equal(targets_before, targets_after)


def test_input_row_order_does_not_change_targets() -> None:
    frame = make_panel()
    decision_date = frame["session_date"].max()
    _, candidates_a, targets_a = generate_targets(frame, decision_date)
    _, candidates_b, targets_b = generate_targets(
        frame.sample(frac=1.0, random_state=42), decision_date
    )
    pd.testing.assert_frame_equal(candidates_a, candidates_b)
    pd.testing.assert_frame_equal(targets_a, targets_b)


def test_split_safe_raw_dollar_volume() -> None:
    frame = make_panel()
    split = frame.copy()
    mask = split["instrument_id"].eq("ID000") & (split["session_date"] >= split["session_date"].sort_values().unique()[250])
    split.loc[mask, "raw_close"] /= 2.0
    split.loc[mask, "raw_volume"] *= 2.0
    # adjusted_close deliberately remains continuous.
    original_features = compute_features(frame)
    split_features = compute_features(split)
    latest = frame["session_date"].max()
    original_adv = original_features.loc[(original_features["instrument_id"] == "ID000") & (original_features["session_date"] == latest), "adv60"].iloc[0]
    split_adv = split_features.loc[(split_features["instrument_id"] == "ID000") & (split_features["session_date"] == latest), "adv60"].iloc[0]
    assert split_adv == pytest.approx(original_adv)


def test_entry_block_and_market_stress_fail_closed() -> None:
    frame = make_panel()
    latest = frame["session_date"].max()
    strongest = "ID023"
    frame.loc[(frame["instrument_id"] == strongest) & (frame["session_date"] == latest), "entry_blocked"] = True
    features = compute_features(frame)
    candidates = select_candidates(features, latest)
    assert strongest not in set(candidates["instrument_id"])
    assert select_candidates(features, latest, market_stress=True).empty


def test_matched_gross_when_one_side_has_only_one_candidate() -> None:
    frame = make_panel()
    features, candidates, _ = generate_targets(frame, frame["session_date"].max())
    reduced = pd.concat(
        [
            candidates.loc[candidates["side"].eq("LONG")],
            candidates.loc[candidates["side"].eq("SHORT")].head(1),
        ],
        ignore_index=True,
    )
    targets = build_target_weights(reduced, features, frame["session_date"].max())
    long_gross = targets.loc[targets["side"].eq("LONG"), "target_weight"].sum()
    short_gross = -targets.loc[targets["side"].eq("SHORT"), "target_weight"].sum()
    assert long_gross == pytest.approx(0.20)
    assert short_gross == pytest.approx(0.20)
    assert targets["target_weight"].sum() == pytest.approx(0.0)


def test_no_target_when_a_side_is_empty() -> None:
    frame = make_panel()
    features, candidates, _ = generate_targets(frame, frame["session_date"].max())
    longs_only = candidates.loc[candidates["side"].eq("LONG")]
    assert build_target_weights(longs_only, features, frame["session_date"].max()).empty


def test_whole_share_allocator_repairs_net_exposure() -> None:
    targets = pd.DataFrame(
        [
            {"instrument_id": "L1", "side": "LONG", "reference_price": 301.0, "target_weight": 0.20},
            {"instrument_id": "L2", "side": "LONG", "reference_price": 199.0, "target_weight": 0.20},
            {"instrument_id": "S1", "side": "SHORT", "reference_price": 83.0, "target_weight": -0.20},
            {"instrument_id": "S2", "side": "SHORT", "reference_price": 61.0, "target_weight": -0.20},
        ]
    )
    allocated = allocate_whole_shares(targets, equity=5_000.0)
    assert bool(allocated["allocation_valid"].iloc[0])
    assert abs(allocated["signed_market_value"].sum()) <= 500.0
    assert (allocated["shares"] >= 0).all()


def test_early_close_decision_time_is_relative_to_official_close() -> None:
    early_close = datetime(2026, 11, 27, 13, 0, tzinfo=NY)
    assert decision_timestamp_from_close(early_close) == pd.Timestamp(
        datetime(2026, 11, 27, 13, 30, tzinfo=NY)
    )


def test_target_record_has_expiring_next_session_window() -> None:
    frame = make_panel()
    latest = frame["session_date"].max()
    _, _, targets = generate_targets(frame, latest)
    close = datetime(2025, 4, 7, 16, 0, tzinfo=NY)
    records = build_target_records(targets, close, "2025-04-08")
    assert records["strategy_id"].eq(STRATEGY_ID).all()
    assert records["decision_timestamp"].iloc[0].hour == 16
    assert records["decision_timestamp"].iloc[0].minute == 30
    assert records["execution_start"].iloc[0].hour == 10
    assert records["expires_at"].iloc[0].hour == 10
    assert records["expires_at"].iloc[0].minute == 30
    assert (records["expires_at"] > records["execution_start"]).all()


def test_sector_cap_skips_third_name_from_same_sector() -> None:
    date = pd.Timestamp("2026-01-05")
    rows = []
    for instrument_id, score, sector in [
        ("A", 3.0, "TECH"),
        ("B", 2.5, "TECH"),
        ("C", 2.0, "TECH"),
        ("D", 1.5, "HEALTH"),
    ]:
        rows.append(
            dict(
                session_date=date,
                instrument_id=instrument_id,
                symbol=instrument_id,
                sector=sector,
                adjusted_close=120.0,
                sma200=100.0,
                mom_12_1=0.2,
                mom_6_1=0.1,
                score=score,
                base_eligible=True,
                cross_section_valid=True,
            )
        )
    manual = pd.DataFrame(rows)
    config = StrategyConfig(
        min_cross_section=2,
        max_longs=3,
        max_shorts=0,
        max_names_per_sector_per_side=2,
    )
    selected = select_candidates(manual, date, config)
    assert selected["instrument_id"].tolist() == ["A", "B", "D"]


def test_price_eligibility_is_separate_from_total_return_series() -> None:
    frame = make_panel()
    frame["price_eligibility_close"] = frame["raw_close"]
    latest = frame["session_date"].max()
    frame.loc[frame["session_date"].eq(latest), "price_eligibility_close"] = 5.0
    features = compute_features(frame)
    day = features.loc[features["session_date"].eq(latest)]
    assert not day["base_eligible"].any()
    assert (day["adjusted_close"] > 5.0).all()

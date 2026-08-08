from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from trading_bot.data.costs import regulatory_sell_fees_usd, select_fee_schedule
from trading_bot.data.errors import DataContractError, PointInTimeError
from trading_bot.data.regulatory_fees import (
    FinraTafRateEntry,
    Section31RateEntry,
    assert_acceptance_period_covered,
    compose_regulatory_fee_schedule,
    validate_contiguous_coverage,
)

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs/data/regulatory_fee_basis.yaml"


def d(value: str) -> date:
    return date.fromisoformat(value)


def load_source_schedules():
    cfg = yaml.safe_load(CONFIG.read_text())
    sec = tuple(
        Section31RateEntry(
            effective_from=d(row["from"]),
            effective_to=d(row["to"]),
            usd_per_million=Decimal(str(row["rate"])),
            source_reference=row["source"],
        )
        for row in cfg["section31_usd_per_million"]
    )
    taf = tuple(
        FinraTafRateEntry(
            effective_from=d(row["from"]),
            effective_to=d(row["to"]),
            usd_per_share=Decimal(str(row["per_share"])),
            maximum_usd_per_trade=Decimal(str(row["cap_per_trade"])),
            source_reference=row["source"],
        )
        for row in cfg["finra_taf_equity"]
    )
    return cfg, sec, taf


def test_official_source_schedules_are_contiguous_over_frozen_window() -> None:
    cfg, sec, taf = load_source_schedules()
    start = d(cfg["coverage"]["effective_from"])
    end = d(cfg["coverage"]["effective_to"])
    validate_contiguous_coverage(sec, coverage_start=start, coverage_end=end, label="Section 31")
    validate_contiguous_coverage(taf, coverage_start=start, coverage_end=end, label="FINRA TAF")


def test_composed_schedule_covers_full_phase03_window_without_ambiguity() -> None:
    cfg, sec, taf = load_source_schedules()
    start = d(cfg["coverage"]["effective_from"])
    end = d(cfg["coverage"]["effective_to"])
    schedule = compose_regulatory_fee_schedule(sec, taf, coverage_start=start, coverage_end=end)
    assert_acceptance_period_covered(schedule, acceptance_start=date(2016, 1, 1), acceptance_end=end)
    for probe in (
        date(2010, 1, 1), date(2016, 2, 16), date(2021, 2, 25),
        date(2024, 5, 22), date(2025, 5, 14), date(2026, 4, 4), end,
    ):
        assert select_fee_schedule(schedule, trade_date=probe).covers(probe)


@pytest.mark.parametrize(
    "trade_date,sec_rate,taf_rate,taf_cap",
    [
        (date(2010, 1, 14), "25.70", "0.000075", "3.75"),
        (date(2010, 1, 15), "12.70", "0.000075", "3.75"),
        (date(2012, 4, 1), "22.40", "0.000095", "4.75"),
        (date(2016, 2, 15), "18.40", "0.000119", "5.95"),
        (date(2016, 2, 16), "21.80", "0.000119", "5.95"),
        (date(2021, 2, 25), "5.10", "0.000119", "5.95"),
        (date(2022, 5, 14), "22.90", "0.000130", "6.49"),
        (date(2023, 2, 27), "8.00", "0.000145", "7.27"),
        (date(2024, 5, 22), "27.80", "0.000166", "8.30"),
        (date(2025, 5, 14), "0.00", "0.000166", "8.30"),
        (date(2026, 1, 2), "0.00", "0.000195", "9.79"),
        (date(2026, 4, 4), "20.60", "0.000195", "9.79"),
    ],
)
def test_effective_date_boundaries(trade_date, sec_rate, taf_rate, taf_cap) -> None:
    cfg, sec, taf = load_source_schedules()
    schedule = compose_regulatory_fee_schedule(
        sec, taf,
        coverage_start=d(cfg["coverage"]["effective_from"]),
        coverage_end=d(cfg["coverage"]["effective_to"]),
    )
    row = select_fee_schedule(schedule, trade_date=trade_date)
    assert row.sec_section31_per_million == Decimal(sec_rate)
    assert row.finra_taf_per_share == Decimal(taf_rate)
    assert row.finra_taf_max_per_trade == Decimal(taf_cap)


def test_finra_taf_cap_is_enforced() -> None:
    cfg, sec, taf = load_source_schedules()
    schedule = compose_regulatory_fee_schedule(sec, taf, coverage_start=date(2010,1,1), coverage_end=date(2026,8,8))
    row = select_fee_schedule(schedule, trade_date=date(2026, 4, 6))
    fees = regulatory_sell_fees_usd(shares=100_000, price=Decimal("100"), schedule=row)
    expected_sec = Decimal("10000000") * Decimal("20.60") / Decimal("1000000")
    assert fees == expected_sec + Decimal("9.79")


def test_finra_low_price_exemption_is_modeled() -> None:
    row = select_fee_schedule(
        compose_regulatory_fee_schedule(
            (Section31RateEntry(date(2026,1,1), date(2026,1,1), Decimal("0"), "SEC"),),
            (FinraTafRateEntry(date(2026,1,1), date(2026,1,1), Decimal("0.000195"), Decimal("9.79"), "FINRA"),),
            coverage_start=date(2026,1,1), coverage_end=date(2026,1,1),
        ),
        trade_date=date(2026,1,1),
    )
    assert regulatory_sell_fees_usd(shares=1000, price=Decimal("0.0001"), schedule=row) == Decimal("0")


def test_gap_or_overlap_fails_closed() -> None:
    rows = (
        Section31RateEntry(date(2020,1,1), date(2020,1,10), Decimal("1"), "a"),
        Section31RateEntry(date(2020,1,12), date(2020,1,20), Decimal("1"), "b"),
    )
    with pytest.raises(DataContractError):
        validate_contiguous_coverage(rows, coverage_start=date(2020,1,1), coverage_end=date(2020,1,20), label="SEC")


def test_acceptance_period_outside_frozen_window_fails() -> None:
    cfg, sec, taf = load_source_schedules()
    schedule = compose_regulatory_fee_schedule(sec, taf, coverage_start=date(2010,1,1), coverage_end=date(2026,8,8))
    with pytest.raises(PointInTimeError):
        assert_acceptance_period_covered(schedule, acceptance_start=date(2009,12,31), acceptance_end=date(2026,8,8))
    with pytest.raises(PointInTimeError):
        assert_acceptance_period_covered(schedule, acceptance_start=date(2016,1,1), acceptance_end=date(2026,8,9))

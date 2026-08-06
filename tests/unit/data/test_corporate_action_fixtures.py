from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from trading_bot.data.total_returns import (
    continuing_event_backward_factor,
    continuing_event_gross_return,
)


FIXTURE_PATH = (
    Path(__file__).parents[2]
    / "fixtures"
    / "data"
    / "corporate_action_economic_cases.json"
)


@pytest.mark.parametrize("case", json.loads(FIXTURE_PATH.read_text()), ids=lambda item: item["case_id"])
def test_registered_corporate_action_economic_case(case):
    previous = Decimal(case["previous_raw_close"])
    ex_close = Decimal(case["ex_close"])
    share_multiplier = Decimal(case["share_multiplier"])
    cash = Decimal(case["cash_per_old_share"])
    noncash = Decimal(case["noncash_value_per_old_share"])
    expected = Decimal(case["expected_gross_return"])

    gross = continuing_event_gross_return(
        previous_raw_close=previous,
        ex_close=ex_close,
        share_multiplier=share_multiplier,
        cash_per_old_share=cash,
        noncash_value_per_old_share=noncash,
    )
    backward = continuing_event_backward_factor(
        ex_close=ex_close,
        share_multiplier=share_multiplier,
        cash_per_old_share=cash,
        noncash_value_per_old_share=noncash,
    )
    assert gross == pytest.approx(expected, abs=Decimal("1e-25"))
    assert ex_close / (previous * backward) == pytest.approx(expected, abs=Decimal("1e-25"))

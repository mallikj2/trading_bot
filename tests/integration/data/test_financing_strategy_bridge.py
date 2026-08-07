from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from trading_bot.data.errors import DataContractError
from trading_bot.data.financing import FinancingBalanceSnapshot, FinancingPolicy, accrue_financing

UTC = timezone.utc


def test_matched_gross_research_accounting_does_not_reuse_short_proceeds():
    snapshot = FinancingBalanceSnapshot(
        session_date=date(2026, 8, 3),
        account_equity_usd=Decimal("5000"),
        long_market_value_usd=Decimal("2500"),
        short_market_value_usd=Decimal("2500"),
        free_cash_usd=Decimal("2500"),
        short_sale_collateral_usd=Decimal("2500"),
        settled_debit_usd=Decimal("0"),
    )
    result = accrue_financing(
        snapshot,
        decision_at=datetime(2026, 8, 3, 20, 30, tzinfo=UTC),
        calendar_days=1,
        policy=FinancingPolicy(),
    )
    assert snapshot.gross_leverage == Decimal("1")
    assert snapshot.net_exposure_usd == 0
    assert result.primary_net_financing_usd == 0


def test_whole_share_or_fee_accounting_cannot_create_hidden_margin_debit():
    snapshot = FinancingBalanceSnapshot(
        session_date=date(2026, 8, 3),
        account_equity_usd=Decimal("5000"),
        long_market_value_usd=Decimal("2500"),
        short_market_value_usd=Decimal("2400"),
        free_cash_usd=Decimal("0"),
        short_sale_collateral_usd=Decimal("2400"),
        settled_debit_usd=Decimal("1"),
    )
    with pytest.raises(DataContractError, match="no-margin-borrowing"):
        accrue_financing(
            snapshot,
            decision_at=datetime(2026, 8, 3, 20, 30, tzinfo=UTC),
            calendar_days=1,
            policy=FinancingPolicy(),
        )

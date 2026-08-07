# Financing Evidence Register

**Reviewed:** 2026-08-06

| Evidence | Finding | Project treatment |
|---|---|---|
| Phase 00 Trading Mandate v0.2 | Initial limited live prohibits leverage and borrowed cash; live shorts require a later separate gate. | Binding. Positive live debit or leverage is prohibited. |
| Phase 01 CSMOM-LS-v0.2 | Primary cash earns zero; financing assumptions are separate; pessimistic financing costs are doubled. | Binding primary/backtest accounting. |
| Schwab Cash Features Disclosure, January 2026 | Free Credit Balance excludes cash collateralizing obligations, including cash resulting from a short sale; cash-feature rates can change daily. | Short-sale proceeds are restricted collateral; no inferred sweep credit. |
| Schwab Brokerage Account Agreement | Cash collateral in Margin and Short Account is not part of available Free Credit Balance; debit interest is charged daily. | Supports restricted collateral and explicit debit accounting. |
| Schwab Margin Rates and Requirements | As reviewed 2026-08-06, effective rate for USD 0–24,999.99 debit is 11.825%; rates can change. | Current deployment evidence only; never historical backfill. |
| FRED DTB3 / Federal Reserve H.15 | Daily 3-month Treasury bill secondary-market rate; FRED labels series Public Domain: Citation Requested. | Optional cash opportunity benchmark only; not broker yield and not primary return input. |

## Web references

- https://www.schwab.com/legal/cash-features-disclosure-statement
- https://www.schwab.com/legal/schwab-brokerage-account-agreement
- https://www.schwab.com/margin/margin-rates-and-requirements
- https://fred.stlouisfed.org/series/DTB3
- https://fred.stlouisfed.org/legal/

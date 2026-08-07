# Transaction Fee Evidence Register

**Reviewed:** 2026-08-06

| Item | Current evidence | Contract treatment |
|---|---|---|
| Schwab listed-stock online commission | Schwab current pricing states USD 0 for online listed stock and ETF trades; industry and stock-borrow fees may still apply. | `online_commission_usd` is explicit. Current USD 0 is evidence for deployment assumptions, not automatically a historical fee series. |
| SEC Section 31 | SEC FY2026 advisory states USD 20.60 per million on covered sales effective 2026-04-04. | Effective-dated sell fee. Missing date coverage fails closed. |
| FINRA TAF | FINRA 2026 schedule states USD 0.000195/share on covered equity sales, capped at USD 9.79/trade. | Effective-dated per-share sell fee with cap. Missing date coverage fails closed. |
| Historical regulatory fees | Not fully enumerated for the intended acceptance interval in this task. | Full schedule required if Phase 03 selects historical-fee mode. |
| Stock-borrow fees | Separate unresolved Phase 02 contract. | Not included in execution fee object; added downstream. |

## Source references

- Charles Schwab pricing pages, reviewed 2026-08-06.
- SEC Section 31 Transaction Fee Rate Advisory for Fiscal Year 2026, February 27, 2026.
- FINRA Fee Adjustment Schedule / 2026 Trading Activity Fee schedule.

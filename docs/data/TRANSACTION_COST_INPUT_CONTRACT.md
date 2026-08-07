# Transaction-Cost Input Contract

**Strategy:** `CSMOM-LS-v0.2`  
**Status:** Input architecture implemented; exact Phase 03 parameters intentionally not frozen  
**Date:** 2026-08-06

## 1. Scope

This contract defines how execution-related costs enter the future backtest. It does not yet choose the exact residual-slippage or market-impact coefficients because the Phase 01/02 reconciliation explicitly deferred those parameter values to Phase 03.

The architecture prevents fees, spread, impact, borrow, dividends, and financing from being collapsed into one opaque number.

## 2. Approved benchmark

The primary research fill benchmark remains the validated next-session **10:00-10:30 ET VWAP**.

The transaction-cost layer does not replace that benchmark. It applies explicit adverse costs around it.

## 3. Price adversity

For a buy:

`adverse_fill = VWAP * (1 + variable_cost_bps / 10,000)`

For a sell:

`adverse_fill = VWAP * (1 - variable_cost_bps / 10,000)`

where:

`variable_cost_bps = half_modeled_spread + residual_slippage + market_impact`

The pre-trade modeled spread is divided by two per side, producing approximately one full modeled spread over an otherwise symmetric round trip.

Using next-day observed NBBO spread directly in the prior-close eligibility rule is prohibited. Observed quotes calibrate the model; the calibrated pre-trade prediction drives the gate and spread-cost input.

## 4. Residual slippage and market impact

The code requires an explicit `TransactionCostAssumptions` object. There is no hidden production default.

Phase 03 must freeze before the final backtest:

- residual slippage bps;
- impact floor bps;
- impact coefficient/model;
- whether regulatory/broker fees use historical schedules or current-deployment economics.

A simple square-root participation input is implemented for controlled experiments:

`impact_bps = max(impact_floor_bps, impact_coefficient_bps * sqrt(order_notional / ADV60))`

Its coefficient is **not Phase 02-approved**.

## 5. Cash charges

Cash charges are kept separate from execution price:

- broker commission;
- SEC Section 31 assessment on applicable covered sales;
- FINRA Trading Activity Fee on applicable covered equity sales.

The fee schedule is effective-dated. Missing or overlapping coverage fails closed.

Current official evidence as of 2026-08-06:

- Schwab lists online exchange-listed stock commissions at USD 0, while noting industry and stock-borrow fees may still apply.
- SEC Section 31: USD 20.60 per USD 1,000,000 of covered sales effective 2026-04-04.
- FINRA 2026 TAF for covered equity securities: USD 0.000195/share, maximum USD 9.79/trade.

These current values are evidence for the contract, not permission to backfill 2026 rates into earlier years. Phase 03 must pre-register the desired fee-basis policy and provide full effective-date coverage where historical fees are selected.

## 6. Costs deliberately outside this module

The following are separately modeled and then added to net P&L:

- stock-borrow fees;
- locate/borrow unavailability;
- recalls and buy-ins;
- financing/margin interest;
- short dividend liabilities and other distributions.

Dividend/distribution economics are already handled by the corporate-action engine. Borrow remains a Phase 02 blocker.

## 7. Pessimistic-cost stress

Phase 01 froze the pessimistic stress at **2x** spread, slippage, fees, borrow, dividend, and financing costs.

The transaction-cost module therefore supports a 2x scenario multiplier, while the exact Phase 03 base inputs remain separately frozen later.

## 8. Required attribution

Every simulated trade must preserve at least:

- benchmark VWAP;
- modeled spread;
- half-spread cost;
- residual slippage;
- market impact;
- commission;
- SEC fee;
- FINRA TAF;
- borrow cost, when implemented;
- dividend/distribution liability;
- financing cost;
- total cost and all-in bps;
- cost-model/configuration version.

No aggregate `slippage` field may hide the decomposition.

## 9. Current gate

The transaction-cost **input architecture passes Phase 02 implementation**. Exact non-spread execution-cost parameters remain intentionally deferred to Phase 03, consistent with the approved reconciliation.

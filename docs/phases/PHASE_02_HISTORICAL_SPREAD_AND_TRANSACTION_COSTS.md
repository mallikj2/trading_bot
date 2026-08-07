# Phase 02 — Historical Spread Calibration and Transaction-Cost Input Design

**Status:** IMPLEMENTATION PASS / CALIBRATION SOURCE BLOCKED  
**Date:** 2026-08-06  
**Strategy:** `CSMOM-LS-v0.2`

## 1. Objective

Close the engineering portion of Phase 02 blocker `B02-05` by defining and implementing a point-in-time historical spread model suitable for the frozen 35 bps do-not-trade rule, while also defining the decomposed transaction-cost inputs required by Phase 03.

This task does not claim that historical quote calibration has been run. It does not freeze the Phase 03 residual-slippage or impact parameters and does not resolve historical short borrow.

## 2. Binding inputs from Phase 01

The implementation preserves these approved rules:

- next-session 10:00-10:30 America/New_York VWAP is the primary fill benchmark;
- new positions are blocked when final modeled spread is above 35 bps;
- base and pessimistic costs must be reported;
- pessimistic costs multiply spread, slippage, fees, borrow, dividends and financing by 2;
- the final acceptance backtest cannot use future information.

## 3. Critical point-in-time decision

The 35 bps rule is evaluated at the strategy decision time after the prior session close.

Therefore **next-session quotes cannot be used directly by the prior-close trade filter**. Historical NBBO is a calibration/validation target only.

The production relationship is:

`completed daily bars -> raw Corwin-Schultz proxy -> historical-only calibration model -> prior-close modeled spread -> 35 bps gate`

The future execution window is used only after it becomes historical training evidence for later model fits.

## 4. Implemented components

### 4.1 NBBO contract

Added typed `NbboQuote` records with:

- stable instrument identity;
- participant/observed timestamp;
- SIP/availability timestamp;
- positive bid/ask;
- bid/ask size;
- sequence number;
- immutable source snapshot lineage;
- data-quality status.

Crossed, non-positive, ambiguous, or untraceable quote states fail closed.

### 4.2 Massive quote adapter

`MassiveClient` now includes historical quote-range retrieval and normalization of documented quote fields:

- `bid_price` / `ask_price`;
- `bid_size` / `ask_size`;
- `participant_timestamp`;
- `sip_timestamp`;
- `sequence_number`.

One-sided zero-price updates are not accepted as complete NBBO calibration states.

Adapter version advanced to `MASSIVE-STOCKS-v0.2.1`.

### 4.3 Observed calibration target

Implemented continuous time-weighted NBBO spread for the exact 10:00-10:30 ET execution window. A valid prevailing quote is required at 10:00 and must be no more than 60 seconds old.

### 4.4 Daily spread proxy

Implemented the Corwin-Schultz two-day high-low estimator. Both bars must be completed, valid and available at the prior-close decision time.

The raw estimator is explicitly labeled a proxy, never an observed spread.

### 4.5 Walk-forward calibration

Implemented robust liquidity-bucket calibration using only target observations already available by fit time.

Buckets use Phase 01 ADV60 boundaries:

- USD 25M-50M;
- USD 50M-100M;
- USD 100M-250M;
- USD 250M+.

The acceptance configuration requires at least 500 calibration points per bucket. Missing buckets fail closed.

### 4.6 Spread gate

The frozen rule is implemented exactly:

- `modeled_spread <= 35 bps`: eligible on spread dimension;
- `modeled_spread > 35 bps`: no new trade.

### 4.7 Transaction-cost decomposition

Implemented typed transaction-cost inputs with separate fields for:

- half-spread;
- residual slippage;
- market impact;
- commission;
- SEC Section 31 fee;
- FINRA TAF;
- total USD cost;
- all-in basis points;
- scenario multiplier.

Stock-borrow, recall/buy-in, financing and distribution liabilities remain separate modules.

## 5. Phase 03 boundary preserved

The approved Phase 01/02 reconciliation deferred exact commission/slippage/impact/financing/borrow-cost parameter values to Phase 03.

Accordingly:

- the code requires an explicit `TransactionCostAssumptions` object;
- no hidden production slippage or impact default is used by the cost builder;
- the 2x pessimistic multiplier remains binding because it was already frozen in Phase 01;
- Phase 03 must pre-register the residual-slippage and market-impact values before the untouched acceptance backtest.

## 6. Provider evaluation and license correction

The spread engine is provider-independent, but the observed-quote source remains unapproved.

A material governance correction was identified during the final source review. Massive's current public Individual Market Data Terms state that, absent another agreement, market data is for display use, restrict non-display and investment-strategy derivative use, and require deletion of market data when an account is terminated/restricted/suspended.

Accordingly, the earlier proposal to use one month of Massive Advanced, retain historical quotes, and downgrade/cancel is **withdrawn under the public individual terms**. The adapter remains tested code, but research use is disabled unless a separate written non-display/research license with acceptable retention rights is approved.

The next quote-source evaluation order is:

1. Databento historical usage-based data — candidate pending exact US-equity quote coverage, request-cost estimate, credentialed sample, and account-specific license/retention review;
2. Cboe DataShop Equity & ETF historical Quotes/Trades — candidate pending exact sample price and license/retention review;
3. any other source meeting the same point-in-time and governance contract.

No purchase or provider approval is authorized by this document.

## 7. Regulatory-fee evidence

Current official evidence was recorded for contract validation:

- Schwab: USD 0 online commission for listed stocks/ETFs; industry and stock-borrow fees may still apply;
- SEC: USD 20.60 per million dollars of covered sales effective 2026-04-04;
- FINRA: 2026 covered-equity TAF USD 0.000195/share, maximum USD 9.79/trade.

These values demonstrate the effective-dated fee model. They are not silently backfilled into prior years.

## 8. Validation

Cumulative validation after this implementation:

- 163 pytest tests passed;
- 12 taxonomy subtests passed;
- future quote targets excluded from earlier calibration fits;
- missing calibration bucket fails closed;
- crossed/stale-start NBBO rejected;
- 35 bps boundary tested;
- Massive quote timestamp/sequence normalization tested;
- regulatory fee gap/overlap detection tested;
- sell-only regulatory-fee application tested;
- cumulative prior Phase 01 and Phase 02 regression remains clean.

## 9. Gate assessment

### Engineering implementation

**PASS**

The historical spread estimator, quote target, walk-forward calibration contract, 35 bps gate and transaction-cost input architecture are implemented and tested.

### Calibration evidence

**BLOCKED / OPEN**

The following remain required before blocker `B02-05` is closed:

1. approved historical quote provider/dataset and executed-use rights;
2. approved acquisition cost and exact coverage period;
3. credentialed deterministic historical quote-panel download;
4. >=500 valid known observations per liquidity bucket;
5. calibration/validation report with coverage and error metrics;
6. frozen calibration artifact and lineage hash.

### Phase 02 overall

**ACTIVE**

Other open blockers also remain, including the credentialed core-provider trial, earnings-source sample/license approval, complex corporate-action provider reconciliation, and historical short-borrow modeling.

## 10. Next task

The next independently executable Phase 02 engineering task is **historical short-borrow availability and borrow-cost modeling**. In parallel, the spread calibration gate needs a licensed historical quote-source trial; the previously proposed Massive one-month-retention path is no longer eligible under the public individual terms.

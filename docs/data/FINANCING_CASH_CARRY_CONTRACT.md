# Phase 02 — Financing and Cash-Carry Contract

**Strategy:** `CSMOM-LS-v0.2`  
**Status:** Implementation PASS  
**Date:** 2026-08-06

## 1. Binding accounting rule

Phase 01 freezes the primary return series with **cash earning zero** and requires financing assumptions to be reported separately. Phase 00 prohibits borrowed cash and leverage during initial limited live. The research target is at most 50% long gross plus 50% short gross.

Therefore:

1. Short-sale proceeds are restricted collateral, not free deployable cash.
2. Short proceeds do not fund the long sleeve.
3. No positive interest credit on short collateral is assumed.
4. Free cash earns zero in the primary acceptance return series.
5. Positive settled debit is a contract violation under the current mandate.
6. An optional cash-opportunity benchmark may be reported separately without changing the primary return series.

## 2. Required rate observation

Every non-zero financing rate must carry:

- `rate_kind`;
- `rate_date`;
- `available_at`;
- `annual_rate` as a decimal;
- day-count basis;
- provider;
- source kind;
- immutable snapshot id;
- revision.

A rate cannot be used before `available_at`. Conflicting latest revisions fail closed.

## 3. Accrual formulas

For balance `B`, annual rate `r`, day-count basis `D`, and calendar days `n`:

`interest = B * r * n / D`

Margin debit cost, if a future mandate version allows it, requires broker-specific evidence. Under the current mandate any positive settled debit raises a data-contract failure.

The Phase 01 pessimistic multiplier applies only to financing **costs**:

`stressed_debit_cost = base_debit_cost * 2`

Positive carry is never doubled under pessimistic stress.

## 4. Cash opportunity benchmark

FRED series `DTB3` may be used as a public historical reference for cash-drag attribution. It is not a representation of the actual Schwab sweep rate and is not credited to the primary strategy return.

The benchmark is optional and is reported as:

`cash_drag = benchmark_cash_income - actual_primary_cash_credit`

With the binding primary analysis, `actual_primary_cash_credit = 0`.

## 5. Short collateral

Schwab's Cash Features disclosure defines cash collateralizing obligations, including a short-sale cash balance, as excluded from Free Credit Balance. This contract therefore does not infer sweep eligibility or interest credit for short proceeds.

## 6. Live/deployment boundary

Current Schwab margin pricing is evidence only for current deployment validation. It must never be backfilled across historical dates. Initial limited live prohibits margin borrowing anyway.

If a future strategy version permits financing:

- exact broker/account cash-feature behavior must be contract-tested;
- historical broker rates must be effective-dated or replaced by a preregistered conservative model;
- the mandate and strategy version must be amended before use.

## 7. Fail-closed cases

- short proceeds counted as free cash;
- gross leverage above 1.0;
- positive settled debit under current mandate;
- future rate revision;
- ambiguous rate revision;
- positive broker cash credit without broker-specific evidence;
- short-collateral interest inferred without explicit broker evidence.

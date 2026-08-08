# Phase 02 — Full Acceptance-Period Regulatory Fee Basis Freeze

**Date:** 2026-08-08  
**Engineering status:** PASS  
**Gate:** `P02-G17 FULL_ACCEPTANCE_PERIOD_REGULATORY_FEE_BASIS` → **PASS**  
**Phase 02:** ACTIVE

## Objective

Freeze a deterministic, effective-dated U.S. equity regulatory-fee basis for the Phase 03 acceptance backtest so historical sell-side regulatory costs cannot be chosen after results are observed.

The frozen basis covers **2010-01-01 through 2026-08-08**. Any Phase 03 acceptance period must be a subset of this interval. A run outside the frozen interval fails closed until the official rate history is extended and re-frozen.

## Scope

The model includes:

- SEC Section 31 covered-sale rate, in USD per million dollars of covered sales;
- FINRA Trading Activity Fee (TAF) for covered equity sales, in USD per share with the effective per-trade cap;
- FINRA's low-price equity rule: no TAF when the per-share execution price is below the applicable per-share TAF rate.

The model excludes:

- broker commissions;
- bid/ask spread and slippage;
- market impact;
- stock-borrow fees;
- financing;
- dividend liabilities;
- exact historical broker customer rounding/pass-through conventions.

Those items are handled by their existing Phase 02 contracts.

## Research interpretation

This is a **regulatory-equivalent research basis**, not an assertion that every historical Schwab customer statement would show the exact same rounded charge.

Section 31 legally applies to self-regulatory organizations, while broker-dealers commonly pass transaction charges through to customers. The research model therefore uses the official effective-dated rate consistently across history and does not claim exact broker invoice reconstruction.

## Frozen coverage

### Section 31

The schedule is reconstructed from SEC Fee Rate Advisories and is stored in:

`configs/data/regulatory_fee_basis.yaml`

It includes every effective-rate interval from 2010-01-01 through 2026-08-08, including mid-year changes and the 2025–2026 zero-rate interval.

Representative boundaries include:

- 2010-01-15: USD 12.70/million;
- 2010-04-01: USD 16.90/million;
- 2011-01-21: USD 19.20/million;
- 2012-02-21: USD 18.00/million;
- 2012-04-01: USD 22.40/million;
- 2013-05-25: USD 17.40/million;
- 2014-03-18: USD 22.10/million;
- 2015-02-14: USD 18.40/million;
- 2016-02-16: USD 21.80/million;
- 2017-07-04: USD 23.10/million;
- 2018-05-22: USD 13.00/million;
- 2019-04-16: USD 20.70/million;
- 2020-02-18: USD 22.10/million;
- 2021-02-25: USD 5.10/million;
- 2022-05-14: USD 22.90/million;
- 2023-02-27: USD 8.00/million;
- 2024-05-22: USD 27.80/million;
- 2025-05-14: USD 0.00/million;
- 2026-04-04: USD 20.60/million.

### FINRA TAF

The frozen equity schedule is:

| Effective interval | USD/share | Cap/trade |
|---|---:|---:|
| 2010-01-01 – 2011-06-30 | 0.000075 | 3.75 |
| 2011-07-01 – 2012-02-29 | 0.000090 | 4.50 |
| 2012-03-01 – 2012-06-30 | 0.000095 | 4.75 |
| 2012-07-01 – 2021-12-31 | 0.000119 | 5.95 |
| 2022-01-01 – 2022-12-31 | 0.000130 | 6.49 |
| 2023-01-01 – 2023-12-31 | 0.000145 | 7.27 |
| 2024-01-01 – 2025-12-31 | 0.000166 | 8.30 |
| 2026-01-01 – 2026-08-08 | 0.000195 | 9.79 |

## Deterministic fee formula

For an eligible covered sale:

```text
section31_fee = sale_notional * section31_usd_per_million / 1_000_000

if execution_price < finra_taf_usd_per_share:
    finra_taf = 0
else:
    finra_taf = min(shares * finra_taf_usd_per_share, finra_taf_cap_per_trade)

regulatory_equivalent_fee = section31_fee + finra_taf
```

The fee schedule is selected by **trade date**, not by backtest build date.

## Fail-closed requirements

Phase 03 must stop if:

- the acceptance start precedes 2010-01-01;
- the acceptance end exceeds the frozen schedule's end date;
- a Section 31 or TAF interval is missing;
- two rate entries overlap for a trade date;
- the schedule/config hash is not recorded with the backtest;
- the fee schedule version is not recorded with the backtest.

## Implementation

New module:

`src/trading_bot/data/regulatory_fees.py`

It provides:

- strongly typed Section 31 and FINRA TAF entries;
- gap/overlap validation;
- deterministic composition into the existing transaction-cost fee contract;
- acceptance-period coverage validation.

The existing `regulatory_sell_fees_usd` calculation was hardened to implement FINRA's low-price TAF exemption.

## Evidence basis

Primary official evidence:

- SEC Fee Rate Advisories index and each named Section 31 transaction-fee advisory covering 2010–2026;
- SEC Section 31 Transaction Fees: Basic Information for Firms;
- FINRA Regulatory Notice 12-31 and predecessor notices for the 2011–2012 TAF changes;
- FINRA SR-FINRA-2020-032 approved fee schedule for 2020–2024;
- FINRA Fee Adjustment Schedule / SR-FINRA-2024-019 for 2024–2029.

See `docs/data/TRANSACTION_FEE_EVIDENCE_REGISTER.md` for the frozen evidence register.

## Validation

Automated tests require:

- complete contiguous Section 31 coverage;
- complete contiguous FINRA TAF coverage;
- exact effective-date boundary selection;
- correct TAF caps;
- correct low-price exemption;
- rejection of gaps and overlaps;
- rejection of an acceptance period outside the frozen window.

## Gate decision

`P02-G17 FULL_ACCEPTANCE_PERIOD_REGULATORY_FEE_BASIS = PASS`

This removes the final `CONDITIONAL` Phase 02 gate. Phase 03 is still **NOT AUTHORIZED** because seven external-evidence gates remain blocked.

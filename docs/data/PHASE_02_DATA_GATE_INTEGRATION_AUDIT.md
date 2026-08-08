# Phase 02 — Data Gate Integration Audit

**Audit date:** 2026-08-08  
**Overall:** `ACTIVE — NOT READY FOR PHASE 03`

## Executive result

The engineering architecture remains coherent and cumulative regression is clean. The core provider retention decision has improved: Kibot's published private-use license satisfies the project's local immutable-retention requirement within the approved personal scope. However, the paid representative trial is still unrun, and Kibot cannot safely serve as the point-in-time security master or sole exact execution source.

The machine-readable audit is `configs/data/phase02_data_gate_audit.yaml`. The runtime gate evaluator in `src/trading_bot/data/gates.py` prohibits Phase 03 authorization unless every mandatory gate is `PASS`.

## Gate summary

| Gate | Status | Phase 03 blocker? |
|---|---|---|
| Phase 01 reconciliation | PASS | No |
| Minimum data kernel | PASS | No |
| Production provider adapters | PASS | No |
| Core provider credentialed representative trial | BLOCKED | **Yes** |
| Core provider retention/private-research license | PASS | No |
| Historical sector engine | PASS | No |
| Full historical-sector coverage crawl | BLOCKED | **Yes** |
| Complex corporate-action/total-return engine | PASS | No |
| Complex-action provider reconciliation — EDI long-history + Databento PIT overlap trial | BLOCKED | **Yes** |
| Revision-aware earnings engine | PASS | No |
| Historical earnings revisions sample/license | BLOCKED | **Yes** |
| Spread/transaction-cost engine | PASS | No |
| Observed quote calibration source/panel | BLOCKED | **Yes** |
| Historical short-borrow engine | PASS | No |
| Historical short-borrow source/license/coverage | BLOCKED | **Yes** |
| Financing/cash-carry engine | PASS | No |
| Full acceptance-period regulatory fee basis | CONDITIONAL | **Yes** |
| PIT security-master and exact-execution source license/trial | BLOCKED | **Yes** |

Result: **10 PASS / 7 BLOCKED / 1 CONDITIONAL** across 18 mandatory gates.

## Core market-data stack decision

### Retained raw EOD archive

Kibot is selected for the first paid retained EOD trial. Its published license permits private use and archival copies and states that already-delivered data may be kept and privately used after subscription cancellation. This approval is scope-bound to the current personal, local, non-redistributed project.

### Point-in-time identity and exact execution

Kibot is not an acceptable sole security master because its documented ticker-change and ticker-reuse behavior can rewrite or concatenate symbol histories. An independent point-in-time identity/listing source is mandatory before a Kibot file can be bound to the local immutable `instrument_id` over a historical interval.

Databento is the preferred next companion trial candidate because its security-master/symbology products are designed around point-in-time listed/delisted securities and historical symbol mappings. Historical trades or equivalent exact records are also required for the Phase 01 10:00–10:30 ET acceptance VWAP.

No Databento account/license/coverage result is claimed yet.


## Corporate-action provider reconciliation architecture

EDI is now the preferred long-history corporate-action candidate because its public historical interface exposes stable event/listing identifiers, record-change timestamps and effective dates, and its historical reference material describes corporate-action/reference change collection since 2003. Databento is the preferred recent PIT overlap source, but its documented corporate-action history begins in 2018 and therefore cannot by itself satisfy the Phase 01 minimum ten-calendar-year horizon. The engineering reconciliation harness is complete; P02-G09 remains blocked until the actual licensed representative trials pass.

## Cross-contract consistency checks

### Timing

- Daily signal data remain bound to official session close plus the approved decision delay.
- Earnings revisions, sector changes, borrow observations, corporate-action revisions, spread calibration models, and financing rates all use `available_at` gates.
- Next-session VWAP/NBBO observations are execution evidence only and cannot leak into prior-close decisions.
- A historical vendor archive does not by itself prove same-day `close + 30 minutes` publication. Same-day signal availability requires a separately validated publication contract/source.

### Identity

All historical datasets are required to map to immutable `instrument_id`; ticker strings remain effective-dated aliases. Kibot ticker values are specifically prohibited from acting as immutable identifiers.

### Prices and economics

- Raw prices remain tradable prices.
- Price eligibility is not total-return adjusted.
- Momentum/trend/volatility use point-in-time total-return economics.
- Short dividend liabilities are handled in the corporate-action layer.
- Stock-borrow fees are handled in the borrow layer.
- Execution costs are handled in the transaction-cost layer.
- Financing is handled separately and cannot duplicate borrow fees or dividends.

### Cash and leverage

- Target gross <= 100%.
- Short proceeds are restricted collateral.
- Cash yield is zero in primary Phase 01 metrics.
- Positive settled debit fails closed.
- Initial limited live remains long-only, unlevered, and without borrowed cash.

## External blockers required before Phase 03

1. Run and pass the paid Kibot representative-case EOD trial under the approved private-research scope.
2. Approve and trial a point-in-time security-master/exact-execution companion (Databento preferred candidate or equivalent).
3. Run the SEC filing-header SIC coverage crawl with a compliant monitored-contact User-Agent and approve coverage/error thresholds.
4. Run and pass the EDI long-history plus Databento PIT-overlap representative corporate-action trial under approved retention/non-display terms.
5. Obtain and validate a revision-aware historical earnings source, including retention rights.
6. Approve a historical quote source and run the preregistered spread-calibration panel.
7. Approve a retainable securities-lending source and run the historical borrow coverage trial.
8. Freeze the acceptance-period regulatory-fee basis before the final backtest.

## Items that do not block Phase 03 historical research

- Schwab live margin debit schedule, because current strategy gross is <= 1.0 and borrowed cash is prohibited.
- Schwab live short authorization, which is a later paper/live gate.
- Actual Schwab cash sweep yield, because primary Phase 01 cash return is frozen at zero.

## Authorization

`PHASE_03_FINAL_ACCEPTANCE_BACKTEST = NOT_AUTHORIZED`

This is a governance state, not a claim that the strategy is invalid. It means the historical evidence chain is incomplete.

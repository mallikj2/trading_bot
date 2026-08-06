# CURRENT_STATE.md — Phase 02 Provider PoC Patch

Apply this patch to the canonical project-state document.

## Active phase

**Phase 02 — Data and Point-in-Time Design**

## Completed Phase 02 work

- Phase 01-to-Phase 02 reconciliation: PASS.
- Provider documentation and contract proof of concept: CONDITIONAL PASS.
- Primary credentialed trial candidate selected: Massive Stocks Developer.
- Free point-in-time enrichment candidate selected: SEC EDGAR.
- Provisional PIT market-cap method defined.
- Provisional sector taxonomy defined: `SEC_SIC_DIVISION_V1`.
- Credentialed trial harness and adversarial fixture tests implemented.

## Phase 02 remains active

The following are not complete:

- Massive credentialed coverage test;
- provider-license retention review;
- earnings schedule revision feed validation;
- spread proxy calibration;
- conservative short-borrow model;
- final Phase 02 acceptance gate.

## Current blockers

1. Revision-aware historical earnings schedule and known-at timestamps.
2. Actual provider evidence for delistings, identity changes, corporate actions, and VWAP completeness.
3. Calibration of `CORWIN_SCHULTZ_CONSERVATIVE_V0_1` against observed quotes.
4. Formal acceptance of SEC SIC as the strategy sector taxonomy.

## Next task

Execute the credentialed Massive provider trial and obtain a Wall Street Horizon DateBreaks sample/quote.

## Authorization state

- Historical strategy acceptance testing: not authorized.
- Paper trading: not authorized.
- Limited live trading: not authorized.
- Live shorting: prohibited.

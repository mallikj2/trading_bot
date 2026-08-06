# CURRENT_STATE.md — Phase 02 Corporate-Action and Total-Return Patch

Apply after the historical-sector patch.

## Active phase

**Phase 02 — Data and Point-in-Time Design**

## Newly completed

- Complex corporate-action contracts implemented.
- Point-in-time action revisions and cancellation handling implemented.
- Complete corporate-action coverage evidence is mandatory.
- Split, reverse split, cash dividend, stock dividend, spinoff, merger, acquisition, delisting, liquidation, and bankruptcy processing implemented.
- Explicit noncash and terminal valuation contracts implemented.
- Raw, split-adjusted, total-return-adjusted, and forward total-return series separated.
- Signed long/short position effects and dividend liabilities implemented.
- Phase 01 strategy input now separates `price_eligibility_close` from `adjusted_close`.
- Local cumulative validation: 119 tests and 12 taxonomy subtests passed.

## Conditional evidence

Provider completeness and accuracy for complex actions remain unproven until the credentialed representative-case trial and retention-license review are completed.

## Phase 02 remains active

Open blockers and conditions:

1. credentialed provider representative-case evidence;
2. provider storage/retention license approval;
3. full SEC historical-sector coverage evidence;
4. historical earnings schedule revisions;
5. historical spread calibration;
6. short-borrow model;
7. provider complex-action and terminal-value coverage evidence;
8. final Phase 02 acceptance gate.

## Authorization state

- Phase 03 final acceptance backtest: not authorized.
- Paper trading: not authorized.
- Limited live trading: not authorized.
- Live shorting: prohibited.

# CURRENT_STATE — Phase 02 Historical Short-Borrow Patch

**Date:** 2026-08-06

## Phase status

`PHASE_02_DATA_AND_POINT_IN_TIME_DESIGN = ACTIVE`

## Newly completed engineering work

- Point-in-time `BorrowObservation` contract implemented.
- Explicit borrow coverage contract implemented.
- Historical versus broker-specific source semantics implemented.
- New-short borrow eligibility gate implemented.
- Existing-short daily continuation/forced-exit gate implemented.
- Recall, buy-in, availability-withdrawal, and broker-restriction events implemented.
- Availability-to-unavailable transition derivation implemented.
- Explicit stock-borrow fee accrual using EOD short market value × annual rate / 360 × calendar days implemented.
- Frozen Phase 01 2x pessimistic borrow-cost multiplier supported.
- ORTEX evaluation adapter guarded behind an explicit research-license approval flag.

## Historical borrow blocker status

`HISTORICAL_SHORT_BORROW_MODEL = IMPLEMENTATION_PASS_SOURCE_BLOCKED`

Still required:

1. approved source license with non-display research and immutable retention rights;
2. credentialed representative historical sample;
3. historical availability/fee/quantity coverage report;
4. missing-row semantics validation;
5. provider identity/ticker-history validation;
6. preregistered recall/withdrawal proxy policy where actual recall history is unavailable;
7. frozen provider snapshot lineage.

## Live Schwab short status

`LIVE_SHORTING = PROHIBITED_PENDING_ACCOUNT_AND_BROKER_BORROW_VALIDATION`

Still required:

- margin-enabled account;
- short permission;
- current broker-specific shortability;
- current borrow fee/quantity where exposed;
- locate/confirmation behavior;
- recall/buy-in/reconciliation tests.

## Source evaluation

- S&P Global Securities Finance: preferred technical fit; commercial/retention terms open.
- DataLend/EquiLend: strong institutional alternative; commercial/retention terms open.
- ORTEX: technically suitable but standard consumer retention terms conflict with kernel immutability/reproducibility.
- IBKR: corroborating broker-specific reference only.
- SEC/FINRA/OCC public datasets: supplemental stress indicators only.

## Remaining Phase 02 open gates

- credentialed representative-case core-provider trial and license approval;
- full historical-sector coverage crawl;
- historical earnings provider sample/license approval;
- complex corporate-action provider reconciliation;
- observed-spread calibration source and credentialed calibration;
- historical short-borrow source and credentialed coverage trial;
- Schwab live borrow/account contract validation.

Phase 03 final acceptance testing remains prohibited.

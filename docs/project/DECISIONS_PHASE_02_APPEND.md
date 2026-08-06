# DECISIONS.md — Phase 02 Reconciliation Append

## DR-P01-003 — Owner approval of CSMOM-LS-v0.2

- **Date:** 2026-08-05
- **Status:** APPROVED — ACTIVE
- **Decision:** Approve `CSMOM-LS-v0.2` as the frozen first strategy research candidate.
- **Approval evidence:** `APPROVE STRATEGY SPEC V0.2`.
- **Effect:** Phase 01 becomes PASS and Phase 02 may be formally entered.
- **No effect:** Does not authorize paper/live orders, live shorting, or performance claims.

## DR-P02-001 — Approve Phase 01 data reconciliation

- **Date:** 2026-08-05
- **Status:** APPROVED — ACTIVE
- **Decision:** Adopt `CSMOM-LS-v0.2-DATA-v0.1` as the controlling Phase 02 reconciliation contract.
- **Result:** Reconciliation PASS; overall Phase 02 remains ACTIVE.
- **Rationale:** The approved strategy requires exact data that were not fully represented in the generic Phase 02 draft, including point-in-time market cap and sector, revision-aware earnings schedules, intraday VWAP, and a historical spread method.
- **Strategy impact:** No frozen Phase 01 threshold is changed.

## DR-P02-002 — Freeze temporal interpretations before backtesting

- **Date:** 2026-08-05
- **Status:** APPROVED — ACTIVE
- **Decision:** Freeze the following pre-result interpretations:
  - monthly universe at the final prior-month close plus 30 minutes;
  - ISO Monday-to-Sunday week and first eligible NYSE session;
  - fill session counts as minimum-hold session 1;
  - rank-buffer size is `max(1, ceil(30% × valid population))` with stable-ID ties;
  - historical adjusted prices are as-of and exclude future corporate actions;
  - final VWAP requires complete 10:00–10:30 ET interval coverage.
- **Reason:** Remove deterministic ambiguity before Phase 03 data are evaluated.
- **Change control:** A change requires a new decision and, when strategy behavior changes materially, a new strategy version.

## DR-P02-003 — Preserve provider-dependent blockers

- **Date:** 2026-08-05
- **Status:** OPEN — BLOCKS PHASE 02 PASS
- **Decision:** Do not waive or silently approximate the point-in-time market-cap, sector-history, earnings-revision, VWAP, spread, identity/action, or short-borrow contracts.
- **Resolution path:** Provider proof of concept, documented derivation, or explicit strategy/mandate amendment before final backtesting.

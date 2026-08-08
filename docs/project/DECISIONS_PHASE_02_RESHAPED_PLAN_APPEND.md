# DECISIONS — Phase 02 Reshaped Plan Append

**Date:** 2026-08-08

| ID | Decision | Status |
|---|---|---|
| D02-PLAN-01 | Insert a mandatory pre-purchase platform-foundation workstream into Phase 02 before commercial account/license procurement | APPROVED |
| D02-PLAN-02 | Preserve all existing 18 Phase 02 data gates and their acceptance semantics | APPROVED |
| D02-PLAN-03 | Keep `CSMOM-LS-v0.2` mathematics and approved timing/universe/risk rules frozen during the platform-foundation work | APPROVED |
| D02-PLAN-04 | Build the Phase 02 UI as read-only; no broker mutation/order controls are permitted | APPROVED |
| D02-PLAN-05 | Build an event journal, deterministic replay, runtime safety states, simulated OMS, and recovery/reconciliation tests before broker integration | APPROVED |
| D02-PLAN-06 | Add dedicated lookahead and recursive/warm-up validation before Phase 03 acceptance backtesting | APPROVED |
| D02-PLAN-07 | Build experiment registry/reporting with synthetic/fixture outputs only until Phase 03 | APPROVED |
| D02-PLAN-08 | Build a future-paper-compatible deterministic simulation runtime, but do not claim or deploy paper trading in Phase 02B | APPROVED |
| D02-PLAN-09 | Defer Phase-02-motivated commercial purchases until `P02-PF-GATE=PASS` and a separate manual procurement decision is recorded | APPROVED |
| D02-PLAN-10 | Passing `P02-PF-GATE` may set `PROCUREMENT_READY_FOR_MANUAL_APPROVAL=true` but never auto-authorizes purchases | APPROVED |
| D02-PLAN-11 | Phase 03 remains prohibited until both `P02-PF-GATE` and all existing mandatory Phase 02 data gates pass, followed by explicit governance authorization | APPROVED |

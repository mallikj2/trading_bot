# DECISIONS.md — Phase 02 Revision-Aware Earnings Append

## DR-P02-034 — Immutable earnings revision stream

**Date:** 2026-08-06  
**Status:** IMPLEMENTED  
**Decision:** Every fiscal-period earnings schedule is stored as immutable revisions with explicit `available_at`. Historical decisions select only the latest version known at the decision time. Current calendars are never backfilled.

## DR-P02-035 — Explicit forward earnings coverage

**Date:** 2026-08-06  
**Status:** IMPLEMENTED  
**Decision:** Absence of an earnings event row is not proof of no event. New entries require a point-in-time coverage record extending through the planned 10-session minimum-hold endpoint.

## DR-P02-036 — Withdrawal and late-revision policy

**Date:** 2026-08-06  
**Status:** IMPLEMENTED  
**Decision:** A withdrawn schedule is unresolved rather than no-event. New entries are blocked; existing positions receive the next available mandatory exit. A late date/time revision never backdates a trade and is recorded as an operational exception.

## DR-P02-037 — Earnings source preference

**Date:** 2026-08-06  
**Status:** PROPOSED / EVIDENCE CONDITIONAL  
**Decision:** Prefer Wall Street Horizon direct historical DateBreaks plus Earnings Date Daily Snapshots for the final acceptance backtest because the public product record explicitly describes revision audit trails and archived as-of calendar states. Approval requires licensed sample and retention review.

## DR-P02-038 — Secondary earnings sources

**Date:** 2026-08-06  
**Status:** IMPLEMENTED CLASSIFICATION  
**Decision:** Massive/Benzinga Earnings is development/corroboration-only until prior schedule revisions are proven retrievable. Intrinio Corporate Events is not eligible as the sole historical source while its official product description states history is most recent data only. SEC/company releases are corroboration-only.

## DR-P02-039 — Earnings task gate

**Date:** 2026-08-06  
**Status:** IMPLEMENTATION PASS / SOURCE CONDITIONAL  
**Decision:** The local revision-aware engine and tests may be merged. Phase 02 cannot pass until the credentialed earnings-source trial and retention-license review are completed.

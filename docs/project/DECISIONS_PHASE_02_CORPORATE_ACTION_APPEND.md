# DECISIONS.md — Phase 02 Corporate-Action and Total-Return Append

## DR-P02-026 — Separate price roles

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Store raw tradable close, current price-eligibility close, split-adjusted close, total-return-adjusted close, and forward total-return index separately. Phase 01 return features use the forward index; the USD 10 threshold uses current-session price eligibility.

## DR-P02-027 — Complete action coverage required

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** An empty corporate-action list is insufficient. Every point-in-time build requires an available complete-coverage record declaring covered action types and a covered-through timestamp.

## DR-P02-028 — Event economic-value formula

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Continuing-event gross return equals post-event parent close multiplied by the share multiplier, plus cash and point-in-time noncash distributions, divided by the prior raw close.

## DR-P02-029 — Noncash valuation policy

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Spinoff and stock-consideration values require explicit, revision-aware, point-in-time valuation records per old parent share. Missing value or currency mismatch blocks processing.

## DR-P02-030 — Terminal event policy

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Merger, acquisition, delisting, liquidation, and bankruptcy events append a terminal return from explicit consideration, stop the parent series, and transform signed positions into cash and/or successor positions. Missing consideration is not interpreted as zero.

## DR-P02-031 — Cancellation and revision policy

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Select the latest action revision available by the decision time. A later cancellation affects only later builds and cannot rewrite earlier frozen datasets.

## DR-P02-032 — Unsupported material actions

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Tender offers, rights distributions, mixed continuing/terminal same-session events, ambiguous same-day terminal bars, and missing ex-date/prior-bar evidence fail closed.

## DR-P02-033 — Corporate-action task gate

**Date:** 2026-08-05  
**Status:** IMPLEMENTATION PASS / PROVIDER COVERAGE CONDITIONAL  
**Decision:** The local engine and tests pass. Final Phase 02 approval still requires credentialed provider evidence and retention-license approval.

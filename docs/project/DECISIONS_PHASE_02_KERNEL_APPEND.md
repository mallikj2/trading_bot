# DECISIONS.md — Phase 02 Minimum Data Kernel Append

## DR-P02-008 — Minimum data-kernel module boundary

**Date:** 2026-08-05  
**Status:** APPROVED FOR IMPLEMENTATION  
**Decision:** Keep provider network access outside the deterministic data kernel. Adapters must preserve raw payloads before normalization into kernel contracts.

**Reason:** Provider behavior and credentials are external concerns; point-in-time rules, identity, hashing, calendars, and universe eligibility must remain provider-independent and directly testable.

## DR-P02-009 — Immutable write semantics

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** A raw snapshot or manifest path may never be overwritten, including with identical content. Corrections require a new snapshot and data version.

## DR-P02-010 — Canonical identity

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Use UUID `instrument_id` as the canonical key. Tickers are half-open effective-dated aliases. Non-overlapping ticker reuse is valid; overlapping exchange/ticker ownership is invalid.

## DR-P02-011 — As-of split adjustments

**Date:** 2026-08-05  
**Status:** IMPLEMENTED FOR SPLITS  
**Decision:** Adjust historical raw prices only for split/reverse-split actions that are effective and available by the decision timestamp. Select the latest known revision for each action ID.

**Limitation:** Total-return cash-dividend and complex-action processing remains a separate Phase 02 task.

## DR-P02-012 — Universe reason completeness

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Frozen monthly membership must retain every applicable rejection reason and a hash of the complete frozen input values.

## DR-P02-013 — Kernel task gate

**Date:** 2026-08-05  
**Status:** PASS  
**Decision:** The minimum data-kernel implementation task passes local acceptance. This does not authorize Phase 03 or close the Phase 02 provider and event-data blockers.

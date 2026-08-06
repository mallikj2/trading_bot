# DECISIONS.md — Phase 02 Production Adapters Append

## DR-P02-014 — Provider network safety

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Provider access is GET-only, host-pinned, rate-limited, retry-bounded, and raw-first. Provider-owned pagination may not leave the configured HTTPS host.

## DR-P02-015 — Credential-gated historical semantics

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Massive dated ticker snapshots, ticker-overview market cap, and ticker-overview SIC cannot be promoted to historical kernel records until a credentialed dated-query trial validates their point-in-time behavior.

## DR-P02-016 — SEC shares availability

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** SEC shares facts require an accession-number join to an exact EDGAR acceptance timestamp plus a conservative processing buffer. Filing date alone is insufficient.

## DR-P02-017 — Multi-class share ambiguity

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Conflicting shares-outstanding values for the same accession and period block market-cap derivation. The adapter does not guess, sum, or choose a class silently.

## DR-P02-018 — SEC SIC correction

**Date:** 2026-08-05  
**Status:** APPROVED CORRECTION  
**Decision:** The SEC submissions top-level SIC field is current-only reference metadata for this project. It cannot satisfy historical sector requirements. Historical sector remains blocked pending an effective-dated source or credentialed proof from another provider.

## DR-P02-019 — Intraday fill completeness

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** The next-session 10:00–10:30 ET VWAP requires every expected interval, positive volume, valid quality, and availability by the simulated fill timestamp. Otherwise no fill is generated.

## DR-P02-020 — Production-adapter task gate

**Date:** 2026-08-05  
**Status:** IMPLEMENTATION PASS / EVIDENCE BLOCKED  
**Decision:** Adapter code passes local acceptance. The provider evidence gate remains blocked because credentials and license approval were unavailable.

# DECISIONS.md — Phase 02 Historical Sector Append

## DR-P02-021 — Filing-level SIC source

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Historical SIC must come from the immutable header of an SEC complete-submission filing associated with the exact target CIK. The current SEC submissions JSON SIC remains current-only.

## DR-P02-022 — Frozen sector taxonomy

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** CSMOM-LS-v0.2 uses `FAMA_FRENCH_12_FROM_SEC_SIC`, version `FF12-SIC-2026-08-05-v1`, for its same-sector selection limit. Mapping ranges are frozen before Phase 03.

## DR-P02-023 — Conservative sector effectiveness

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** A filing-time classification becomes effective only at EDGAR acceptance plus the configured processing buffer. No earlier economic effective date is inferred.

## DR-P02-024 — Sector null and conflict policy

**Date:** 2026-08-05  
**Status:** IMPLEMENTED  
**Decision:** Missing, zero, ambiguous, conflicting, or not-yet-available SIC blocks sector emission. A decision before the first valid filing observation has no sector and fails closed.

## DR-P02-025 — Historical-sector task gate

**Date:** 2026-08-05  
**Status:** IMPLEMENTATION PASS / COVERAGE CONDITIONAL  
**Decision:** The source and implementation pass local acceptance. Final Phase 02 approval still requires a full-universe coverage scan and manual review of representative sector changes.

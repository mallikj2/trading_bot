# DECISIONS.md — Phase 02 Provider PoC Append

## DR-P02-003 — Primary provider trial

**Date:** 2026-08-05  
**Status:** PROPOSED FOR APPROVAL  
**Decision:** Use Massive Stocks Developer as the primary credentialed trial for price, reference, corporate-action, and intraday data.

**Rationale:** It documents ten years of US stock history and minute aggregates at USD 79/month, remaining within the approved USD 80 recurring ceiling.

**Limitations:** No earnings revisions, historical borrow, or Developer-plan historical quotes. Ticker-event coverage requires trial validation.

## DR-P02-004 — Point-in-time market-cap method

**Date:** 2026-08-05  
**Status:** PROPOSED FOR APPROVAL  
**Decision:** Derive issuer market capitalization from point-in-time SEC shares facts and raw class prices when security-class mapping is unambiguous.

**Fail-closed rule:** Exclude ambiguous multi-class issuers or facts that were not available by the monthly universe freeze.

## DR-P02-005 — Provisional sector taxonomy

**Date:** 2026-08-05  
**Status:** PROPOSED FOR APPROVAL  
**Decision:** Use effective-dated SEC filing-header SIC mapped to `SEC_SIC_DIVISION_V1` for the first acceptance experiment.

**Reason:** This is reproducible, filing-timestamped, free, and compatible with the data budget. It is not interchangeable with GICS and must be named explicitly in all results.

## DR-P02-006 — Earnings revision blocker

**Date:** 2026-08-05  
**Status:** RECORDED  
**Decision:** Do not backfill current earnings calendars. Seek a revision-aware historical sample from Wall Street Horizon DateBreaks or raise a Phase 01 amendment.

## DR-P02-007 — Historical spread candidate

**Date:** 2026-08-05  
**Status:** PROPOSED; CALIBRATION REQUIRED  
**Decision:** Evaluate `CORWIN_SCHULTZ_CONSERVATIVE_V0_1` as the modeled historical spread method when observed quote history is unavailable.

**Restriction:** It cannot support final acceptance until the preregistered quote-calibration gate passes.

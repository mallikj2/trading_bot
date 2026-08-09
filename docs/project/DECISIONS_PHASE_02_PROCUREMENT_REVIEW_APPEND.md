# DECISIONS append — P02-PROCUREMENT-REVIEW

## D-P02-PR-01 — Minimum-spend procurement sequencing

**Decision:** PASS the procurement review and stage external evidence acquisition from lowest/no-cost to custom/enterprise spend.  
**Date:** 2026-08-08

Sequence starts with SEC configuration, Databento free historical credits/quotes, and one $14 Kibot EOD month after explicit user approval. Custom WSH/EDI/borrow spend is deferred until trials and licensing terms pass.

## D-P02-PR-02 — Kibot retained archive approved for purchase recommendation

**Decision:** The current public Kibot private-use license is sufficient to recommend a one-month EOD purchase for the retained core-price trial because it explicitly permits archival copies and permanent private retention/use of already-delivered data after cancellation/lapse/termination.

This is a purchase recommendation, not `PROCUREMENT_AUTHORIZED=true`. Provider trial evidence is still required before P02-G04 can pass.

## D-P02-PR-03 — Databento trial before paid monthly plan

**Decision:** Do not purchase a Databento monthly US-equities market-data plan merely to execute historical Phase 02 trials. Use the current $125 signup historical credits and usage-based historical pricing first.

Full-US PIT Security Master coverage is a separate entitlement issue: the 1,000-symbol flexible entry plan is not assumed sufficient for the historical US universe. Obtain an exact full-US quote and account-specific research/retention confirmation before G18/G07 closure.

## D-P02-PR-04 — S3 Partners requires retention amendment

**Decision:** S3 Partners' AWS securities-finance dataset becomes the first low-cost technical candidate for G15, but its standard AWS DSA terms are not acceptable for the permanent immutable archive because termination/expiration can require data removal within 90 days.

Request a custom/private offer or written amendment. If not available, proceed to S&P Global Securities Finance/DataLend quotes.

## D-P02-PR-05 — Standard ORTEX rejected

**Decision:** Do not buy standard ORTEX API/Data Services for the Phase 02 historical borrow archive. Published terms prohibit a persistent independent archive and require deletion after termination.

## D-P02-PR-06 — EDI/WSH trial-first policy

**Decision:** Request no-cost samples/trials and written retention/internal-use terms before accepting any EDI or Wall Street Horizon quote. Public marketing on perpetual ownership/trials is supporting evidence, not final account-license approval.

## D-P02-PR-07 — No automatic spending

**Decision:** `PROCUREMENT_READY_FOR_MANUAL_APPROVAL=true` does not imply spending authority. Keep:

```text
PROCUREMENT_AUTHORIZED=false
PHASE03_AUTHORIZED=false
```

until the user explicitly approves the procurement action/limits.

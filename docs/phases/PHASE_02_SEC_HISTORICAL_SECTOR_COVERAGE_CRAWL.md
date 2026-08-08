# Phase 02 — SEC Historical Sector Coverage Crawl

**Version:** 0.1.0  
**Date:** 2026-08-08  
**Gate:** P02-G07  
**Task status:** IMPLEMENTATION PASS / REAL COVERAGE CRAWL BLOCKED  
**Phase status:** ACTIVE / PHASE 03 NOT AUTHORIZED

## 1. Objective

Turn the existing filing-header SIC engine into a reproducible, resumable, full-coverage validation pipeline for the Phase 01 sector constraint.

The final acceptance test is not “can a SIC be parsed?” It is:

> At least 99% of sector-blind, otherwise-eligible historical instrument decision points must have a sector classification that was actually available by that decision timestamp, with no silent future fallback and with traceable raw SEC evidence.

## 2. Critical dependency correction

The previous project note implied that P02-G07 could be completed once a compliant SEC User-Agent was supplied. That was incomplete.

The 99% denominator must be produced by the historical universe **before sector is applied**. Otherwise survivorship or circular filtering could make sector coverage appear better than it is.

Therefore a real P02-G07 run requires both:

1. a compliant `SEC_USER_AGENT` identifying the application and a monitored contact email; and
2. a sector-blind PIT target ledger generated from the historical universe / security-master stack.

The second dependency remains upstream of unresolved P02-G04/P02-G18 evidence. No current ticker list may substitute for it.

## 3. Canonical filing inventory

The crawler now uses SEC **daily master indexes** as the canonical filing inventory.

SEC documents that post-acceptance removals processed on later business days are not reflected backward into previous daily indexes. This is important because a current submissions history can otherwise omit a filing that was historically visible.

Canonical inventory path:

```text
/Archives/edgar/daily-index/{year}/QTR{quarter}/master.{yyyymmdd}.idx
```

Quarter directory discovery uses:

```text
/Archives/edgar/daily-index/{year}/QTR{quarter}/index.json
```

The SEC Submissions API may still be used for acceleration or corroboration, but it is not the canonical historical filing inventory for this gate.

## 4. Filing-header evidence

For each target CIK/accession identified by the as-published daily indexes, the crawler fetches the SEC complete-submission text and applies the previously approved exact-CIK SIC parser.

The implementation persists:

- raw daily master indexes;
- raw complete-submission text;
- immutable manifests and hashes;
- accession-to-SIC observations;
- acceptance and conservative availability timestamps;
- crawl failures and checkpoint state.

A mutable operational checkpoint is allowed only to resume downloads. Raw provider evidence remains append-only and immutable.

## 5. Availability correction

The filing-header publication buffer is changed from **1 minute to 3 minutes**.

SEC's current Webmaster FAQ states that filings are often available on sec.gov within approximately 1–3 minutes of the EDGAR system timestamp. For a fail-closed historical sector model, the upper end of that documented normal range is used:

```text
sector.available_at = EDGAR accepted_at + 3 minutes
```

This is a conservative correction to a prior implementation assumption, not a change to the approved Phase 01 strategy.

## 6. Post-acceptance correction risk

SEC also documents post-acceptance corrections and removals.

The daily-index inventory protects against later removals disappearing from the historical inventory. A current complete-submission copy, however, may reflect later corrections. Therefore the acceptance runbook requires manual original-archive (`Oldloads`) review of at least 25 detected sector-change cases.

A currently missing complete submission is never interpreted as “no filing.” It remains unresolved and blocks affected history until recovered from an original daily archive or otherwise resolved.

## 7. Target ledger contract

Each required row must contain:

```text
instrument_id
cik
 decision_at
source_manifest_hash
universe_version
```

The ledger must declare:

```text
sector_blind = true
```

CIK is effective-dated upstream. A current issuer CIK must not be copied backward where the security master indicates otherwise.

## 8. Acceptance criteria

P02-G07 can become PASS only when all of the following hold:

1. coverage ratio >= 99% of sector-blind otherwise-eligible decision points;
2. unresolved selected filing headers = 0;
3. every detected FF12 sector change is traceable to accession + immutable raw snapshot;
4. no overlapping sector intervals exist;
5. at least 25 real sector-change cases are manually approved;
6. zero manually reviewed cases are rejected;
7. legacy and modern filing-header fixtures pass;
8. no future filing satisfies an earlier decision;
9. missing sector continues to block entry/universe inclusion.

## 9. Implementation delivered

New implementation includes:

- daily EDGAR master-index parser;
- quarter directory discovery;
- CIK filtering;
- immutable raw index persistence;
- resumable index and filing checkpoints;
- complete-submission retrieval and SIC parsing;
- sector-blind target-ledger parser;
- point-in-time coverage evaluator;
- per-CIK coverage summaries;
- 99% acceptance calculation;
- manual sector-change review contract;
- fail-closed CLI runner;
- machine-readable blocked/complete result output.

## 10. Execution result in this environment

The actual runner was invoked.

It returned `BLOCKED` because:

```text
SEC_USER_AGENT_WITH_MONITORED_CONTACT_REQUIRED
SECTOR_BLIND_TARGET_LEDGER_REQUIRED_FROM_UPSTREAM_PIT_UNIVERSE
```

No SEC full-universe coverage percentage or manual-review completion is claimed.

## 11. Gate decision

### Engineering implementation: PASS

The crawler, coverage evaluator, checkpointing, and fail-closed behavior are implemented and tested.

### P02-G07 real evidence: BLOCKED

The real evidence run requires the external monitored-contact SEC header and the upstream sector-blind PIT target ledger.

### Phase 02: ACTIVE

Phase 03 remains prohibited while P02-G07 and the other external-evidence gates remain unresolved.

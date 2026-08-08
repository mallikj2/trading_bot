# SEC Historical Sector Coverage Crawl Contract

**Version:** 0.1.0  
**Gate:** P02-G07

## Target denominator

Coverage is measured against a sector-blind upstream ledger. Sector itself must not participate in creating the denominator.

Each row requires a stable `instrument_id`, effective CIK, UTC `decision_at`, upstream manifest hash, and universe version.

## Filing inventory

Canonical inventory is the as-published SEC daily `master.YYYYMMDD.idx` series. This is selected because SEC states later post-acceptance removals are not rewritten into previous daily indexes.

A conflicting duplicate accession is a dataset-blocking error.

## Filing content

The selected filing is represented by immutable SEC complete-submission text. The parser must find the exact target CIK and one non-zero assigned SIC.

Missing, conflicting, or ambiguous SIC is unresolved. The crawler does not substitute SEC's current top-level SIC.

## Point-in-time availability

```text
available_at = EDGAR acceptance timestamp + 3 minutes
```

The 3-minute buffer is the conservative upper bound of SEC's currently documented typical 1–3 minute filing-publication lag.

Future filings never backfill an earlier requirement.

## Coverage calculation

```text
coverage_ratio = covered_sector_blind_decision_points / required_sector_blind_decision_points
```

Acceptance requires `coverage_ratio >= 0.99`.

In addition:

- unresolved selected filing headers must be zero;
- interval overlap count must be zero;
- all sector changes must retain source snapshot lineage;
- at least 25 actual sector changes must have approved manual reviews;
- no reviewed change may be rejected;
- representative modern and legacy header tests must pass.

## Post-acceptance corrections

Daily indexes preserve the existence of later-removed filings, but current archived filing content may reflect later metadata corrections.

At least 25 detected sector changes must therefore be compared to original daily archive evidence (`Oldloads`) during the real acceptance run. A removed current filing must be recovered from original archival evidence rather than treated as nonexistent.

## Resume semantics

Operational checkpoints may be overwritten because they are process state, not research evidence.

Raw SEC daily indexes and complete-submission responses are immutable snapshots with hashes and manifests.

## Fail-closed cases

- missing monitored-contact SEC User-Agent;
- missing sector-blind target ledger;
- current-only/security-surviving target list;
- invalid or conflicting CIK/accession;
- missing complete submission without archival recovery;
- missing/0000/conflicting SIC;
- coverage below 99%;
- unresolved filing count > 0;
- overlapping sector intervals;
- untraceable sector change;
- fewer than 25 approved real change reviews;
- any rejected manual review.

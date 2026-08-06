# Phase 02 — Historical Sector Classification

**Version:** 0.1  
**Date:** 2026-08-05  
**Task status:** IMPLEMENTATION PASS / COVERAGE CONDITIONAL  
**Phase status:** ACTIVE

## 1. Objective

Resolve the Phase 01 requirement for point-in-time sector classification without copying a current classification backward through history.

## 2. Decision

Use the assigned SIC embedded in each immutable SEC complete-submission filing header. Map the filing-time four-digit SIC into a frozen Fama–French 12-sector taxonomy.

This supersedes only the earlier assumption that the SEC submissions JSON top-level SIC might provide history. That top-level field remains current-only and prohibited for historical use.

## 3. Implemented

- host-pinned, GET-only SEC Archives text client;
- complete-submission archive path construction;
- legacy SGML and modern text-header parsing;
- exact target-CIK selection for multi-entity filings;
- accession, form, SIC, and acceptance-timestamp validation;
- immutable raw-snapshot lineage field;
- frozen FF12 SIC mapping;
- conservative effective intervals;
- point-in-time sector selection;
- no-future-fallback behavior;
- monthly-universe integration test;
- ambiguous and conflicting record rejection.

## 4. Point-in-time interpretation

The filing header proves the classification visible in EDGAR at that filing. It does not prove the true economic date when the issuer's business changed.

Therefore:

```text
sector effective_from = filing accepted_at + processing buffer
```

This treatment may lag an economic change, but it prevents look-ahead bias.

## 5. Acceptance evidence

- 70 Phase 02 tests passed;
- 19 approved Phase 01 tests passed in the merged repository;
- 89 merged tests passed in total;
- 12 explicit taxonomy boundary subtests passed;
- Python compilation passed;
- YAML parsing passed;
- deterministic bundle manifest validation passed.

## 6. Remaining coverage gate

The implementation does not claim full historical coverage. Before final Phase 02 approval, run a compliant SEC crawl using a real monitored User-Agent and verify:

1. at least 99% coverage of otherwise-eligible instrument-months;
2. no overlapping sector intervals;
3. traceability of every interval to an accession and raw snapshot;
4. manual review of at least 25 detected sector changes;
5. missing classifications block entry and universe inclusion.

## 7. Gate decision

### Implementation: PASS

The source, contracts, parsing, taxonomy, and point-in-time logic are ready for merge.

### Coverage evidence: CONDITIONAL

Full-universe SEC archive collection was not run in this environment. The historical-sector blocker is reduced from “source unknown” to “coverage evidence pending.”

### Phase 02: ACTIVE

Still open:

1. credentialed Massive representative-case trial;
2. provider retention-license approval;
3. SEC sector-coverage crawl;
4. historical earnings revisions;
5. historical spread calibration;
6. short-borrow modeling;
7. complex corporate actions and total-return processing;
8. final Phase 02 acceptance gate.

## 8. Next task

Implement complex corporate-action and total-return processing while external provider and coverage evidence remains pending.

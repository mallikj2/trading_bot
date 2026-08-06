# Phase 02 — Minimum Data Kernel

**Version:** 0.1  
**Date:** 2026-08-05  
**Task status:** PASS  
**Phase status:** ACTIVE

## 1. Objective

Implement the minimum deterministic data foundation required by the approved Phase 01 strategy and the reconciled Phase 02 point-in-time contract.

## 2. Implemented scope

The repository bundle implements:

1. immutable raw-file and manifest writes;
2. SHA-256 raw-file and canonical content hashing;
3. stable UUID instrument identity and effective-dated ticker aliases;
4. typed daily-bar, corporate-action, listing, market-cap, sector, earnings, feature, and universe contracts;
5. generic latest-known point-in-time revision selection;
6. feature availability propagation from all inputs;
7. versioned exchange-session calendars;
8. official-close-plus-30-minute decision timestamps, including early closes;
9. prior-month-final-session universe freeze timing;
10. as-of split and reverse-split price adjustment;
11. complete Phase 01 monthly universe eligibility reason codes;
12. deterministic universe hashes;
13. future-information and lineage leakage checks;
14. unit and integration tests for adversarial cases.

## 3. Phase 01 reconciliation

The universe builder uses the frozen `CSMOM-LS-v0.2` boundaries:

- NYSE/Nasdaq common stocks;
- adjusted close at least USD 10;
- point-in-time market cap at least USD 2 billion;
- median raw-dollar-volume ADV60 at least USD 25 million;
- at least 300 valid sessions;
- annualized VOL20 no greater than 80%;
- effective-dated sector required;
- valid identity, listing state, data quality, and corporate-action state.

The builder does not invent missing provider values. Missing values produce explicit rejection reasons.

## 4. Acceptance evidence

### Unit tests

Thirty-eight tests pass across:

- contracts and naive-datetime rejection;
- invalid OHLC rejection;
- immutable storage and source mutation detection;
- deterministic manifest hashing;
- future-revision exclusion;
- latest-known revision selection;
- ticker changes and ticker reuse;
- identity overlap rejection;
- regular and early-close sessions;
- prior-month universe freeze timing;
- future-action exclusion;
- corrected corporate-action revisions;
- exact universe boundaries and complete reason codes;
- future-information scans and lineage hashes.

### Integration and regression tests

One end-to-end deterministic rebuild test verifies that identical raw bytes and normalized universe inputs produce identical manifest and membership hashes.

The bundle was also overlaid on the approved Phase 01 repository bundle. All 19 Phase 01 strategy tests remained green, alongside the 38 kernel unit tests and one kernel integration test.

### Compilation

All source and test modules compile successfully.

## 5. Scope limitations

This task does not complete the following Phase 02 blockers:

- credentialed Massive provider coverage evidence;
- provider retention-license review;
- filing-to-share-class SEC market-cap production adapter;
- formal approval of `SEC_SIC_DIVISION_V1`;
- revision-aware historical earnings feed;
- 10:00–10:30 ET VWAP production fill engine;
- Corwin–Schultz spread calibration;
- conservative historical borrow model;
- full cash-dividend and complex-action total-return processing.

## 6. Gate decision

### Minimum data-kernel task: PASS

The code satisfies the defined minimum implementation task and is ready to merge behind provider adapters.

### Phase 02: ACTIVE / CONDITIONAL

Phase 03 final historical acceptance testing remains prohibited until the outstanding provider, earnings, spread, borrow, and action-processing gates are closed.

## 7. Next Phase 02 task

Implement and validate the first production adapter path:

1. Massive immutable raw ingestion for reference, daily, action, and minute data;
2. SEC submissions/company-facts ingestion with accession and acceptance timestamps;
3. normalized adapter output into this kernel;
4. credentialed representative-case report.

The earnings-revision data-source decision can proceed in parallel, but current-only calendars remain prohibited.

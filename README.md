# Phase 02 Regulatory Fee Basis Freeze Bundle

Cumulative repository-ready Phase 02 bundle through `P02-G17 FULL_ACCEPTANCE_PERIOD_REGULATORY_FEE_BASIS`.

## New in this bundle

- frozen SEC Section 31 history from 2010-01-01 through 2026-08-08;
- frozen FINRA covered-equity TAF history over the same interval;
- deterministic rate composition and acceptance-period coverage validator;
- FINRA low-price TAF exemption;
- regulatory fee contract and official evidence register;
- updated transaction-cost config;
- updated Phase 02 integration audit and machine gate state;
- P02-G17 promoted from CONDITIONAL to PASS.

## Current gate state

```text
18 mandatory gates
11 PASS
7 BLOCKED
0 CONDITIONAL
PHASE03_AUTHORIZED=false
```

The seven remaining gates require external licensed data, provider credentials, or external coverage evidence.

See:

- `docs/phases/PHASE_02_REGULATORY_FEE_BASIS_FREEZE.md`
- `docs/data/REGULATORY_FEE_BASIS_CONTRACT.md`
- `docs/data/TRANSACTION_FEE_EVIDENCE_REGISTER.md`
- `VALIDATION_RESULTS.md`

## Latest Phase 02 increment — SEC historical sector coverage crawl

This cumulative bundle adds the P02-G07 crawl/evidence layer:

- `src/trading_bot/data/sector_coverage.py`
- `src/trading_bot/data/adapters/sec_sector_crawl.py`
- `configs/data/sec_sector_coverage_crawl.yaml`
- `docs/phases/PHASE_02_SEC_HISTORICAL_SECTOR_COVERAGE_CRAWL.md`
- `docs/data/SEC_SECTOR_COVERAGE_CRAWL_CONTRACT.md`
- `docs/data/SEC_SECTOR_COVERAGE_RUNBOOK.md`
- `SEC_SECTOR_COVERAGE_RESULTS.json`

The engineering is complete, but P02-G07 remains BLOCKED until the real sector-blind PIT target ledger and compliant monitored-contact SEC User-Agent are available.

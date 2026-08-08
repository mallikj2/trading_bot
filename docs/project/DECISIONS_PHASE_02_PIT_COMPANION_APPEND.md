# DECISIONS — Phase 02 PIT Security-Master / Execution Append

**Date:** 2026-08-08

| ID | Decision | Status |
|---|---|---|
| D02-PIT-01 | Treat provider `ts_record` as the earliest provider-knowledge time and require both `ts_effective <= decision_at` and `ts_record <= decision_at` | APPROVED |
| D02-PIT-02 | Use provider security/listing identifiers as identity; ticker remains an alias | APPROVED |
| D02-PIT-03 | Prefer stable FIGI/US-code/ISIN symbology for historical execution requests | APPROVED |
| D02-PIT-04 | Build P02-G07's denominator using all frozen Phase 01 universe rules except sector | APPROVED |
| D02-PIT-05 | Missing PIT CIK for an otherwise-eligible security is an upstream failure, not a sector exclusion | APPROVED |
| D02-PIT-06 | Permit PIT security-master shares outstanding only as an alternate/corroborating market-cap path until credentialed reconciliation | APPROVED |
| D02-PIT-07 | Require trade-level size-weighted 10:00–10:30 ET VWAP for final execution evidence; OHLC approximation remains prohibited | APPROVED |
| D02-PIT-08 | Require a separately reviewed execution-coverage profile before any Databento/equivalent dataset can satisfy the market-wide Phase 01 execution benchmark | APPROVED |
| D02-PIT-09 | Keep P02-G04 and P02-G18 BLOCKED until real account/license and representative data evidence pass | APPROVED |

# Phase 02 PIT Security-Master and Exact-Execution Integration Bundle

Cumulative repository-ready Phase 02 bundle through the internal P02-G04/P02-G18 integration layer.

## New in this bundle

- hardened PIT security-master normalization using both `ts_effective` and `ts_record`;
- stable provider security/listing identity and ticker-reuse detection;
- approval-gated stable-ID historical trade queries;
- exact DST-aware 10:00–10:30 ET trade VWAP;
- separate execution-coverage governance gate;
- PIT shares-outstanding market-cap corroboration;
- sector-blind monthly universe/target-ledger builder for P02-G07;
- direct integration test from PIT identity to SEC target-ledger parsing;
- standalone credentialed PIT companion runner;
- machine-readable representative acceptance policy.

## Current gate state

```text
18 mandatory gates
11 PASS
7 BLOCKED
0 CONDITIONAL
PHASE03_AUTHORIZED=false
```

P02-G04 and P02-G18 remain BLOCKED because no approved Databento/equivalent account license, execution coverage profile, or credentialed representative trial is present. P02-G07 remains blocked until the real sector-blind ledger and monitored-contact SEC crawl are completed.

See:

- `docs/phases/PHASE_02_PIT_SECURITY_MASTER_AND_EXECUTION_INTEGRATION.md`
- `docs/data/PIT_SECURITY_MASTER_EXECUTION_CONTRACT.md`
- `docs/data/PIT_COMPANION_REPRESENTATIVE_TRIAL_RUNBOOK.md`
- `configs/data/pit_security_master_execution_acceptance.yaml`
- `PIT_COMPANION_TRIAL_RESULTS.json`
- `VALIDATION_RESULTS.md`

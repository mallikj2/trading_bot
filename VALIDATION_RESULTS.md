# Validation Results — Phase 02 Core Provider Selection and Trial

**Date:** 2026-08-08  
**Task status:** `LICENSE DECISION PASS / CREDENTIALED TRIAL BLOCKED`  
**Phase 02 status:** `ACTIVE — NOT READY FOR PHASE 03`

## Cumulative automated tests

Command:

```bash
PYTHONPATH=src pytest -q tests
```

Result:

```text
219 passed, 12 subtests passed
```

The cumulative suite includes the approved Phase 01 strategy tests and all Phase 02 kernel, provider adapters, sector, corporate action/total return, earnings, spread/cost, short-borrow, financing, gate-audit, and new Kibot/core-provider tests.

## New core-provider focused tests

```text
14 passed
```

Coverage includes:

- Kibot paid-client license acknowledgement gate;
- guest-evaluation boundary;
- session/cookie login transport behavior;
- unadjusted daily-history request contract;
- daily/minute/tick parsing;
- Eastern Time bar-open conversion into UTC kernel timestamps;
- exact size-weighted trade VWAP calculation;
- adjustment-description parsing without unproven ratio inference;
- credentialed-trial environment status;
- approval-gated Databento PIT security-master range request;
- Databento historical `trades` schema request with explicit dataset configuration;
- blocked trial result when credentials/approved companion evidence are absent.

## Credentialed representative-case trial

The executable runner was invoked in this environment.

Observed environment:

```text
KIBOT_USERNAME/KIBOT_PASSWORD: MISSING
KIBOT_PRIVATE_RESEARCH_LICENSE_APPROVED: NO
DATABENTO_API_KEY: MISSING
DATABENTO_RESEARCH_LICENSE_APPROVED: NO
DATABENTO_US_EQUITIES_DATASET: MISSING
SEC_USER_AGENT: MISSING
```

Result:

```text
CORE_PROVIDER_TRIAL_RESULTS.json: BLOCKED
```

No paid provider request, data-quality coverage result, or credentialed accuracy claim is made.

## Compilation and artifact parsing

- Python `compileall`: PASS
- YAML parse: 12 files PASS
- JSON parse: 7 files PASS
- Machine-readable audit: 18 mandatory gates = 10 PASS / 7 BLOCKED / 1 CONDITIONAL
- `P02-G05 CORE_PROVIDER_RETENTION_AND_NON_DISPLAY_LICENSE`: PASS within Kibot private/personal scope
- `P02-G04 CORE_PROVIDER_CREDENTIALED_REPRESENTATIVE_CASE_TRIAL`: BLOCKED
- `P02-G18 PIT_SECURITY_MASTER_AND_EXACT_EXECUTION_SOURCE_LICENSE_AND_TRIAL`: BLOCKED

## Evidence not claimed

The following remain open and are **not** claimed as passed:

- paid Kibot representative-case trial;
- Databento or equivalent PIT security-master/exact-execution license and coverage trial;
- same-day EOD publication timing suitable for a 16:30 ET historical decision contract;
- full historical-sector coverage crawl;
- complex corporate-action provider reconciliation;
- licensed historical earnings revision sample;
- licensed observed-spread calibration dataset/panel;
- licensed historical securities-lending coverage;
- full acceptance-period regulatory fee basis;
- Schwab live short/account/borrow authorization;
- Schwab live cash-feature/margin contract testing.

## Gate result

### Core provider private-retention license

**PASS — scope-bound to the personal local project**

### Credentialed provider trial

**BLOCKED**

### Phase 02 final data gate

**NOT READY**

### Phase 03 final acceptance backtest

**NOT AUTHORIZED**

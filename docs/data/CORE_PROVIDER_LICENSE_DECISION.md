# Phase 02 — Core Provider License Decision

**Decision date:** 2026-08-08  
**Decision:** Approve Kibot for retained private EOD research archives; do not approve it as the sole point-in-time security master.

## Scope of approval

For this personal, local, non-redistributed research platform, Kibot's published license is compatible with the Phase 02 immutable-archive requirement because it:

- grants private use to the licensee;
- permits archival copies;
- prohibits resale/redistribution/transfer;
- explicitly states that already-delivered data may be kept permanently after a subscription ends and may continue to be used and archived privately.

The project therefore classifies Kibot raw snapshots as:

`PRIVATE_PERSONAL_RESEARCH_RETAINABLE`

This approval is **scope-bound**. Any company use, multi-user use, redistribution, hosted service, client reporting, or institutional deployment requires a new license review or written custom license.

## Product fit

The current public EOD subscription is $14 per 30-day billing cycle and advertises up to 64 years of EOD history for stocks/ETFs plus unadjusted, split-adjusted, and fully adjusted variants. The research adapter always requests/preserves the **unadjusted** view. Adjustments are reconstructed by the local point-in-time corporate-action engine.

## Critical identity limitation

Kibot is **not** the approved security master. Its own documentation states that:

- ticker renames move old history into the new symbol file;
- reused tickers can place two unrelated issuers in one symbol file;
- liquid delisted names are generally retained but very thin delisted securities can be absent.

Accordingly, a Kibot symbol file may only be attached to a local `instrument_id` after an independent point-in-time identity/listing source proves the issuer interval. Current symbol lists cannot be backfilled historically.

## Execution-data limitation

Kibot 1-minute OHLCV does not provide exact within-bar trade VWAP. The final Phase 01 benchmark requires exact 10:00–10:30 ET VWAP from validated intraday evidence. Kibot tick data can theoretically support exact trade VWAP, but the all-stocks tick package is currently far more expensive than the EOD plan. The preferred companion evaluation is therefore Databento historical trades/security-master data under a separate license/trial gate.

## Governance outcome

- `P02-G05 CORE_PROVIDER_RETENTION_AND_NON_DISPLAY_LICENSE`: **PASS**, limited to private personal research under Kibot's published license.
- `P02-G04 CORE_PROVIDER_CREDENTIALED_REPRESENTATIVE_CASE_TRIAL`: **BLOCKED** until paid Kibot credentials and representative evidence are run.
- `P02-G18 PIT_SECURITY_MASTER_AND_EXECUTION_SOURCE_LICENSE_AND_TRIAL`: **BLOCKED** until a companion source is licensed and trialed.

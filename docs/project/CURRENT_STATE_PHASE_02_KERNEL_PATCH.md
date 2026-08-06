# CURRENT_STATE.md — Phase 02 Minimum Data Kernel Patch

Apply this patch after the Phase 02 provider-PoC patch.

## Active phase

**Phase 02 — Data and Point-in-Time Design**

## Newly completed

- Minimum data-kernel implementation task: PASS.
- Immutable snapshots and dataset manifests implemented.
- Stable instrument identity and effective-dated aliases implemented.
- Daily-bar and corporate-action contracts implemented.
- Generic point-in-time revision selector implemented.
- Versioned exchange-calendar and early-close timing implemented.
- Monthly Phase 01 universe builder and complete reason codes implemented.
- Leakage and deterministic-rebuild tests implemented.
- Local validation: 38 unit tests and 1 integration test passed.

## Phase 02 remains active

Open evidence and implementation items:

1. credentialed Massive provider trial and retention-license review;
2. SEC production ingestion and security-class market-cap mapping;
3. final sector-taxonomy approval;
4. revision-aware historical earnings schedule;
5. production intraday VWAP normalization;
6. historical spread calibration;
7. conservative short-borrow model;
8. complex corporate-action and total-return processing;
9. final Phase 02 acceptance gate.

## Authorization state

- Phase 03 final acceptance backtest: not authorized.
- Paper trading: not authorized.
- Limited live trading: not authorized.
- Live shorting: prohibited.

## Next task

Implement the first production provider adapters against the minimum data kernel and run the credentialed representative-case trial when credentials are available.

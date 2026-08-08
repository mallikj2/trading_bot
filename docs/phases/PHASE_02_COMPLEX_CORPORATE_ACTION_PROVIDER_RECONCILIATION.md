# Phase 02 — Complex Corporate-Action Provider Reconciliation

**Date:** 2026-08-08  
**Engineering status:** PASS  
**External evidence status:** BLOCKED  
**Phase 02:** ACTIVE

## Objective

Close the design/engineering portion of P02-G09 by selecting the external corporate-action evidence stack and building a fail-closed reconciliation harness against the already-approved point-in-time total-return engine.

## Delivered

- provider-neutral corporate-action evidence contract;
- point-in-time revision resolution with explicit reconciliation cut-off;
- ambiguity blocking for conflicting same-revision rows;
- ambiguity blocking for multiple distinct same-day provider events;
- economic reconciliation for splits, reverse splits, cash dividends, stock distributions, spinoffs, mergers/acquisitions and terminal events;
- mandatory successor/outturn checks for spinoffs and stock mergers;
- EDI WCA historical-export normalizer;
- approval-gated Databento corporate-actions Reference API adapter;
- executable representative-trial runner;
- six official-source golden economic cases;
- machine-readable provider-reconciliation policy.

## Selected provider stack

### EDI — preferred long-history event master

EDI is selected for the next negotiated trial because its public historical API includes revision/change timestamps and event identifiers, its material describes corporate-action/reference history collected since 2003, and it advertises perpetual-ownership licensing options. Actual project rights remain subject to the executed client-specific agreement.

### Databento — preferred recent PIT overlap source

Databento is selected as the independent recent-history cross-check. It has rich listing-level PIT corporate-action data but documents history from 2018-05-01, so it cannot by itself satisfy the strategy's minimum ten-calendar-year acceptance horizon.

### Kibot — simple adjustment corroboration only

Kibot may corroborate split/dividend adjustment behavior but cannot close complex-event or identity reconciliation.

## Point-in-time behavior

For a reconciliation cut-off `T`, provider rows with `available_at > T` are invisible. Revisions are resolved per stable provider event ID. If the latest known revision is internally conflicting, reconciliation blocks. If more than one distinct provider event still matches the same kernel action type and economic date, reconciliation blocks instead of guessing.

This prevents a later correction/cancellation from rewriting an earlier historical decision.

## Representative cases

The committed fixture includes:

- NVDA 2024 forward split;
- GE 2021 reverse split;
- IBM/Kyndryl 2021 spinoff;
- Xilinx/AMD 2022 stock acquisition;
- Twitter 2022 cash merger;
- Bed Bath & Beyond 2023 zero-recovery bankruptcy.

These fixtures encode official economic truth only; they do not fabricate provider observations.

## Trial result in this environment

The executable trial runner was invoked. It returned BLOCKED because no approved EDI representative export, EDI license approval flag, Databento corporate-actions API key, or Databento corporate-actions license approval flag is available here.

No licensed provider accuracy or completeness result is claimed.

## Gate decision

### Engineering / offline validation

**PASS**

### P02-G09 complex corporate-action provider reconciliation

**BLOCKED** — `EDI_LONG_HISTORY_AND_DATABENTO_PIT_OVERLAP_REPRESENTATIVE_TRIAL_NOT_RUN`

### Phase 03

**NOT AUTHORIZED**

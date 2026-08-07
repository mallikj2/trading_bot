# Phase 02 — Revision-Aware Historical Earnings Schedule

**Version:** 0.1  
**Date:** 2026-08-06  
**Status:** IMPLEMENTATION PASS / SOURCE CONDITIONAL  
**Depends on:** Approved CSMOM-LS-v0.2 Phase 01 specification and Phase 02 point-in-time kernel

## 1. Objective

Implement a historical earnings-calendar contract that reproduces only the schedule state known at each strategy decision time and prevents a current earnings calendar from leaking later date/time changes into earlier decisions.

## 2. Approved Phase 01 rules preserved

- BMO and unknown-time earnings: exit prior trading session.
- During-session earnings: treat as BMO.
- AMC earnings: exit on the event trading session.
- New entry blocked when the scheduled event falls inside the 10-session planned minimum holding interval.
- Mandatory earnings exits override minimum hold.
- Re-entry only from a decision after the event session's validated close.
- Late revisions generate an operational exception and next available mandatory exit; historical trades are not rewritten.

## 3. Implemented contracts

### Immutable revisions

`EarningsScheduleRevision` stores fiscal-event identity, date, timing, schedule status, revision kind, provider availability timestamp, local ingestion timestamp, source lineage, and immutable revision number.

### Explicit forward coverage

`EarningsCoverageObservation` prevents an empty provider result from being interpreted as proof that no earnings event exists. A new entry requires complete coverage through the minimum-hold endpoint.

### Point-in-time selectors

The implementation selects the latest revision satisfying:

```text
available_at <= decision_at
```

No future fallback exists.

### Entry engine

`evaluate_new_entry()` calculates the next-session fill, 10-session hold endpoint, provider coverage, latest-known schedules, unresolved withdrawals, and post-event re-entry boundary.

### Exit engine

`required_earnings_exit_session()` implements the BMO/AMC/during/unknown mapping.

`plan_existing_position_exit()` explicitly distinguishes:

- not yet due;
- scheduled mandatory exit;
- late schedule revision;
- unresolved/withdrawn schedule.

A missed historical deadline is never backdated.

## 4. Source evaluation

### Preferred acceptance source

Wall Street Horizon direct historical **DateBreaks + Earnings Date Daily Snapshots** is the preferred source candidate because public documentation explicitly describes timestamped earnings-date revisions, audit trails, archived calendar snapshots, and historical as-published data.

### Secondary sources

- Massive/Benzinga Earnings: development/corroboration only unless a credentialed trial proves prior versions are retrievable. Public documentation exposes `last_updated`, date, time, and projected/confirmed status but does not prove immutable historical revisions.
- Intrinio Corporate Events: rejected as the sole historical source because its product page states `History: Most recent data only`.
- SEC/company releases: corroboration only; insufficient as a complete forecast/tentative calendar history.

## 5. Evidence boundary

This task does **not** claim:

- access to Wall Street Horizon licensed historical files;
- exact WSH schema fields;
- a WSH price quote;
- local-retention rights;
- full-universe earnings coverage;
- provider accuracy/completeness.

Those remain credentialed-trial and license-review evidence.

## 6. Adversarial cases covered

The local tests cover:

- later date revisions invisible to prior decisions;
- events moved earlier or later;
- AMC/BMO/unknown/during-session mapping;
- AMC-to-BMO late time revisions;
- weekend unknown-time events;
- withdrawn dates;
- missing forward coverage;
- status-only revisions;
- duplicate/invalid revision sequences;
- impossible ingestion timestamps;
- non-retroactive historical decisions.

## 7. Acceptance criteria for the source trial

The preferred source is approved only when:

1. provider historical snapshots reconstruct every tested as-of calendar state;
2. revision timestamps expose no future information;
3. stable issuer/event identity is deterministic;
4. BMO/AMC/time changes are machine-readable and consistent;
5. withdrawals/reschedules are represented safely;
6. every strategy-admitted decision has explicit forward coverage;
7. immutable raw storage and lineage hashes reproduce results;
8. local archive, internal backtest, derived-output retention, and termination obligations are contractually approved.

## 8. Gate

### Task result: IMPLEMENTATION PASS / SOURCE CONDITIONAL

The point-in-time earnings schedule engine is sufficiently implemented and tested to proceed with other independent Phase 02 work.

### Phase 02 remains ACTIVE

The following remain open:

1. credentialed provider representative-case trial;
2. provider retention-license approval;
3. Wall Street Horizon historical earnings sample and schema validation;
4. full SEC historical-sector coverage evidence;
5. complex corporate-action provider reconciliation;
6. historical spread calibration;
7. historical short-borrow modeling;
8. final Phase 02 acceptance gate.

Phase 03 final acceptance testing remains unauthorized.

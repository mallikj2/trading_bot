# Earnings Provider Credentialed Trial Runbook

## Objective

Prove that the preferred earnings source can reconstruct the schedule state actually known at each historical Phase 01 decision timestamp.

## Required trial material

Request a historical sample containing both DateBreaks/revision history and daily earnings-calendar snapshots for a period containing:

- at least 10 issuers;
- at least 20 fiscal-period earnings events;
- at least 5 date changes;
- at least 3 timing changes;
- BMO and AMC events;
- at least one unknown/unspecified timing event when available;
- at least one status transition from forecast/tentative to confirmed;
- at least one withdrawal/cancellation/reschedule case when available;
- delisted or renamed issuers where supported;
- several daily snapshots before and after each revision.

The sample should include source identifiers and original provider timestamps.

## Procedure

1. Store every provider file/message unchanged in immutable raw storage.
2. Hash and manifest each source object.
3. Map provider identity to local `instrument_id` without using a future ticker alias.
4. Normalize each change into `EarningsScheduleRevision`.
5. Normalize snapshot completeness into `EarningsCoverageObservation`.
6. For each sample decision timestamp, select only revisions with `available_at <= decision_at`.
7. Compare reconstructed state to the corresponding provider daily snapshot.
8. Re-run the same query after importing later revisions and prove earlier selected states do not change.
9. Test BMO, AMC, unknown, and timing-change exit mapping.
10. Test an earlier-date revision that makes the required exit deadline impossible; verify the engine records a late operational exception rather than backdating a trade.
11. Verify every admitted new-entry decision has coverage through its 10-session minimum-hold endpoint.
12. Record all schema ambiguities and provider corrections.

## Required PASS evidence

- Zero future revisions visible to earlier decisions.
- Zero ambiguous duplicate event identities in the trial after documented mapping rules.
- Reconstructed as-of schedule state matches provider historical snapshots for every tested decision date.
- BMO/AMC/timing classifications map deterministically to Phase 01 exit sessions.
- Withdrawn/rescheduled events are not silently interpreted as no event.
- Absence of a row is never accepted without explicit forward coverage.
- Raw provider objects and normalized lineage are reproducible by hash.
- License review confirms local archival, research/backtesting, derived-output retention, and termination obligations.

## Failure handling

Any material timestamp ambiguity, inability to retrieve prior states, unexplained snapshot/revision disagreement, or prohibited local retention causes `FAIL` for that source. The project must not compensate by backfilling the current calendar.

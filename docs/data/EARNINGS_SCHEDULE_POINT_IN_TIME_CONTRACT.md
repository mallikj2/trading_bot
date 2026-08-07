# CSMOM-LS-v0.2 — Revision-Aware Earnings Schedule Contract

**Version:** 0.1  
**Date:** 2026-08-06  
**Authority:** Approved Phase 01 strategy specification and Phase 02 point-in-time policy

## 1. Strategy behavior preserved

The Phase 01 rules are binding:

- the strategy does not intentionally hold through scheduled earnings;
- BMO and unknown-time earnings require the prior trading session's 10:00–10:30 ET exit window;
- AMC earnings require the event session's 10:00–10:30 ET exit window;
- during-session earnings are treated like BMO;
- a new entry is blocked if the planned 10-session minimum holding interval contains a scheduled earnings event;
- re-entry is permitted only from a decision after the event session's validated close;
- a late schedule revision creates an operational exception and the next available mandatory exit; history is not rewritten.

## 2. Immutable schedule revision

Every schedule version requires:

| Field | Contract |
|---|---|
| `instrument_id` | stable local UUID |
| `event_key` | stable fiscal-event identity across revisions |
| `fiscal_year` / `fiscal_period` | required |
| `scheduled_session` | event calendar date; nullable only when withdrawn/unresolved |
| `timing` | `BMO`, `AMC`, `DURING_SESSION`, `UNKNOWN` |
| `status` | `FORECAST`, `TENTATIVE`, `CONFIRMED`, `WITHDRAWN`, `COMPLETED` |
| `revision_kind` | initial/date/time/status/withdrawal/restore/correction |
| `available_at` | earliest UTC instant historical strategy may know this revision |
| `ingested_at` | local immutable ingestion time |
| `revision` | strictly increasing within `event_key` |
| `source_snapshot_id` | immutable lineage |
| `provider` | provider name |
| `source_event_id` | provider event ID when available |
| `source_url` | source evidence where licensed/available |
| `confidence` | source confidence/status metadata |

Selection rule:

```text
latest revision
where event_key matches
  and available_at <= decision_at
order by available_at, revision
```

There is no future fallback.

## 3. Forward-coverage contract

An empty event result is never interpreted as "no earnings" by itself.

Each instrument requires an `EarningsCoverageObservation` proving that the source was complete through at least the last session of the planned minimum holding interval.

```text
coverage.complete == true
coverage.covered_through >= minimum_hold_end_session
coverage.available_at <= decision_at
```

If this cannot be proved, the new entry is blocked.

This protects against provider outages, missing symbols, incomplete snapshots, mapping failures, and calendar feeds that only expose a subset of upcoming events.

## 4. Entry policy

For a decision after session `D`:

```text
fill_session = next_session(D)
minimum_hold_end = 10th session including fill_session
```

A new entry is blocked when any latest-known event is scheduled between `fill_session` and `minimum_hold_end`, inclusive.

All forecast, tentative, and confirmed schedules are risk events. Confidence or confirmation status is observability metadata and must not be optimized after seeing returns.

A withdrawn date is not evidence that the earnings event disappeared. Until a replacement schedule or completion state is known, the event is unresolved and new entry is blocked.

## 5. Exit policy

| Timing | Required exit session |
|---|---|
| BMO | prior trading session |
| UNKNOWN | prior trading session |
| DURING_SESSION | prior trading session |
| AMC | event trading session |

Normal research execution is the required session's 10:00–10:30 ET VWAP window.

### Late revisions

Because the initial strategy makes deterministic decisions after the validated close, the earliest normal execution opportunity is the next trading session.

If a newly known schedule implies a required exit session earlier than the next available execution session:

- do not backdate the exit;
- set `late_revision = true`;
- record `operational_exception = true`;
- execute at the next permitted 10:00–10:30 ET window;
- retain the revision timestamp and missed required session in attribution.

A date withdrawal or unresolved schedule for an existing position is treated as an event-data invalidation and forces the next available mandatory exit.

## 6. Re-entry

For an event on a normal trading session, re-entry is permitted only after that session's validated close-plus-30-minute decision point.

For a weekend/holiday event date, re-entry is conservatively delayed until after the first subsequent trading session's validated close.

## 7. Revision-history validation

For each event key:

- instrument and fiscal identity must remain stable;
- revision numbers strictly increase;
- `(available_at, revision)` keys are unique;
- timestamps are timezone-aware UTC internally;
- active schedules require an event date;
- provider availability cannot be later than local ingestion in an impossible direction (`ingested_at < available_at` is rejected);
- source snapshots are immutable.

## 8. Historical backtest admissibility

A historical instrument-decision row is admissible only when:

1. stable instrument identity is resolved;
2. earnings revision history is available as-of the decision;
3. forward coverage extends through the minimum hold end;
4. timing class is valid or safely mapped to `UNKNOWN`;
5. lineage is reproducible;
6. no provider correction has been retroactively substituted for what was historically known.

Missing earnings coverage blocks the affected entry. It does not authorize assuming that no earnings event existed.

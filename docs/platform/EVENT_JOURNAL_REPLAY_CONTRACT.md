# Event Journal + Deterministic Replay Contract

**Phase task:** P02-PF03  
**Status:** PASS  
**Scope:** local research/simulation platform foundation only

## Purpose

Provide a persistent, append-only audit backbone that can later support runtime safety, OMS state, simulation, incident handling, recovery, and reconciliation without allowing historical facts to be rewritten.

PF03 is not a broker integration and does not authorize paper/live trading.

## Domain event contract

Every `DomainEvent` contains:

- deterministic `event_id` (SHA-256 of the canonical event body);
- `event_type`;
- `aggregate_type` and `aggregate_id`;
- UTC `occurred_at`;
- `correlation_id`;
- optional `causation_id`;
- producer name;
- positive schema version;
- canonical JSON object payload.

`recorded_at` is **not** part of the domain event. It is journal storage metadata. Re-ingesting the same domain event after a restart therefore remains idempotent even if the new ingestion attempt happens later.

### Determinism restrictions

- JSON object keys are canonicalized and sorted.
- Native binary floating-point payload values are rejected.
- Decimal/price/rate values must be serialized as strings.
- Naive timestamps are rejected and aware timestamps are normalized to UTC.
- Historical correction means appending a new event; an existing event is never updated.

## Journal storage contract

The initial implementation uses standard-library SQLite with a **single serialized writer**. Multiple readers are safe, but PF03 does not claim multi-process/multi-writer event publication. Later runtime work must preserve this single-writer boundary or introduce an explicitly tested coordinator.

Each persisted record adds:

- monotonic `sequence`;
- UTC `recorded_at`;
- `previous_chain_hash`;
- `chain_hash`.

SQLite triggers reject `UPDATE` and `DELETE` at the storage layer.

The journal chain is:

```text
chain_hash[n] = SHA256(
    sequence[n]
    + event_id[n]
    + recorded_at[n]
    + chain_hash[n-1]
)
```

with an all-zero SHA-256 genesis value.

`verify_integrity()` must prove:

1. contiguous journal sequence;
2. valid immutable event IDs/payloads;
3. valid previous-hash linkage;
4. valid recomputed chain hashes;
5. causation refers only to an earlier event;
6. a caused event retains the cause event's correlation ID.

A direct/offline database modification that bypasses SQLite triggers must still be detected by event-ID or chain verification.

## Replay contract

Replay order is authoritative journal sequence, not event occurrence time.

A projector must expose:

- an empty initial state;
- deterministic `apply(state, event)` behavior;
- a canonical JSON-safe projection snapshot.

PF03 hashes the canonical projection snapshot with SHA-256. Identical journal input and projector version must produce the identical state hash.

### TradeLead projection

PF03's first projector consumes:

```text
TRADE_LEAD.SNAPSHOT
```

The payload contains a full PF01 `TradeLead` snapshot. Replay delegates merge/conflict rules to `TradeLeadBook`, preserving PF01 guarantees:

- immutable research content cannot change;
- duplicate snapshots are idempotent;
- stale snapshots cannot regress state;
- lifecycle history must be monotonic;
- divergent lifecycle branches fail replay.

The projection is versioned as `TRADE_LEAD_BOOK_V1`.

## Replay CLI

Local journal integrity/replay can be checked with:

```bash
PYTHONPATH=src python -m trading_bot.platform.replay_cli var/event_journal/platform_events.sqlite3
```

Optional historical reconstruction:

```bash
PYTHONPATH=src python -m trading_bot.platform.replay_cli \
  var/event_journal/platform_events.sqlite3 \
  --through-sequence 125
```

The command reports the journal head hash, event range, event count, projection state hash, and projection snapshot.

## Hard boundaries

PF03 does not provide:

- broker connectivity;
- order submission or cancellation;
- provider credentials;
- deployed paper trading;
- live account state;
- mutable historical events;
- Phase 03 authorization.

Runtime event types for risk state, OMS, incidents, and reconciliation will be added only by their owning Phase 02B tasks.

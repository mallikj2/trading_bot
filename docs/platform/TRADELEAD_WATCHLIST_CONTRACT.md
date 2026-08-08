# TradeLead + Watchlist Domain Contract

**Task:** P02-PF01  
**Version:** 1.0.0  
**Authority:** Phase 02B pre-purchase platform foundation

## 1. Purpose

`TradeLead` is the canonical research decision artifact passed from strategy/research into later portfolio, risk, UI, audit, OMS, simulation, and eventual execution-planning layers.

It is not an order and has no broker authority.

A lead freezes the evidence that existed at its decision timestamp. Later lifecycle events may record that risk, costs, borrow, portfolio constraints, or execution planning blocked the opportunity, but those events cannot rewrite the original signal score, factors, strategy version, or point-in-time provenance.

## 2. Immutable research identity

A lead ID is deterministic from:

- internal `instrument_id`;
- strategy ID/version;
- decision timestamp;
- LONG/SHORT direction;
- dataset manifest hash;
- universe manifest hash;
- feature manifest hash.

Reprocessing the same decision inputs therefore resolves to the same logical lead ID. If the same ID appears with different frozen research content, the `TradeLeadBook` raises a conflict rather than selecting one silently.

A current/display ticker is presentation metadata only. The historically valid `decision_symbol` remains frozen and its availability timestamp must be no later than the decision time.

## 3. Point-in-time guarantees

Every factor observation carries `available_at` and must satisfy:

`factor.available_at <= decision_at`

The provenance envelope additionally stores `max_input_available_at`, which must also satisfy:

`max_input_available_at <= decision_at`

The decision symbol follows the same rule. A later display-symbol change can be attached for UI presentation without altering the lead ID or decision symbol.

## 4. Lifecycle

The state set is:

`DISCOVERED, WATCHLIST, QUALIFIED, RISK_REJECTED, EVENT_BLOCKED, COST_BLOCKED, BORROW_BLOCKED, PORTFOLIO_REJECTED, PLANNED, ENTERED, EXIT_PENDING, CLOSED, EXPIRED`

Every lead begins with a deterministic creation transition into `DISCOVERED`.

Important fail-closed rule: a WATCHLIST or blocked/rejected lead does not later rewrite itself into QUALIFIED. If a future strategy decision has improved score/trend/universe conditions, that future decision creates a new lead artifact. This prevents later information from retroactively changing the original research decision.

A QUALIFIED or PLANNED lead may become rejected/blocked when later operational evidence becomes known. Those transitions preserve the original score/factors.

`PLANNED`, `ENTERED`, `EXIT_PENDING`, and `CLOSED` require an explicit proposed whole-share allocation.

`CLOSED` and `EXPIRED` are terminal.

## 5. Reasons

Reasons are structured records containing:

- stable reason code;
- human-readable deterministic detail;
- availability timestamp;
- blocking flag.

Blocked lifecycle states require a matching reason category. Examples:

- `EVENT_BLOCKED` → earnings/event reason;
- `COST_BLOCKED` → spread/cost reason;
- `BORROW_BLOCKED` → borrow reason;
- `RISK_REJECTED` → risk/market-stress reason;
- `PORTFOLIO_REJECTED` → capacity/sector/correlation/whole-share reason.

Reasons used in a state transition must have been available no later than the transition timestamp.

## 6. Watchlist projection

`derive_watchlist_entry()` produces a read model containing:

- lead ID/instrument/symbol/direction;
- current lifecycle state;
- frozen score;
- explicit blocking reasons;
- deterministic "what must change" actions;
- validity horizon;
- source lead content hash.

The watchlist action text is mapped from stable reason codes. It is not generated post-hoc by an LLM and therefore cannot invent a reason that was absent from the deterministic decision record.

## 7. Idempotency and conflict behavior

The `TradeLeadBook` supports:

- duplicate snapshots → no-op;
- lifecycle-history extensions → accepted;
- stale snapshots → ignored;
- presentation-symbol updates with monotonic as-of time → accepted;
- same ID with changed score/factors/provenance → rejected;
- divergent lifecycle histories → rejected;
- allocation rewrites → rejected.

This registry is in-memory for PF01. PF03 will introduce the persistent append-only event journal.

## 8. Serialization

`TradeLead` supports deterministic JSON round-trip serialization. Decimal values serialize as strings, timestamps as timezone-aware ISO-8601 values, UUIDs as strings, and hashes as lowercase SHA-256 hex.

The object exposes:

- immutable research fingerprint;
- full content hash.

These hashes are intended for later API, journal, replay, experiment, and audit integration.

## 9. Hard safety boundary

PF01 contains:

- no network I/O;
- no broker dependency;
- no live or paper order command;
- no secret handling;
- no strategy-parameter mutation.

It cannot submit, cancel, modify, or authorize an order.

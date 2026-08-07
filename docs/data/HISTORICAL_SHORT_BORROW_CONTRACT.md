# Historical Short-Borrow Point-in-Time Contract

## Required record

Each usable borrow observation must contain:

| Field | Requirement |
|---|---|
| `instrument_id` | Stable internal UUID |
| `provider` | Required |
| `environment` | Research / paper / live context |
| `source_kind` | Broker-specific, market-composite, or regulatory proxy |
| `observed_at` | UTC-aware |
| `available_at` | UTC-aware and not earlier than observation |
| `expires_at` | UTC-aware and later than availability |
| `availability` | AVAILABLE / UNAVAILABLE / UNKNOWN |
| `difficulty` | EASY / HARD / UNKNOWN |
| `annual_fee_rate` | Decimal annual rate; missing blocks final entry |
| `available_shares` | Required when quantity policy is enabled |
| `revision` | Non-negative |
| `source_snapshot_id` | Immutable lineage |
| `locate_or_confirmation_id` | Required where the broker workflow provides one |

## As-of rule

For decision time `tau`, a borrow observation is eligible only when:

`available_at <= tau < expires_at`

Among eligible records the latest `(available_at, observed_at, revision)` is selected. Multiple different records at the same maximum key are an ambiguity defect and fail closed.

## Entry rule

Historical short entry requires all of:

1. approved provider;
2. valid unexpired point-in-time record;
3. `availability == AVAILABLE`;
4. known annual fee rate;
5. adequate quantity when quantity is part of the source contract;
6. no active recall, buy-in, availability-withdrawal, or broker restriction;
7. hard-to-borrow policy passes;
8. explicit rate/economic ceiling passes if configured.

## Continuation rule

Every open short is rechecked daily after the validated close. Unknown, expired, unavailable, recalled, restricted, or uneconomic borrow requires an exit at the next strategy-permitted execution window.

## Missing rows

Missing observations are never interpreted as free or easy-to-borrow.

A provider may supply a `BorrowCoverageObservation` declaring dense daily coverage. This allows the system to distinguish a genuine provider gap from lack of dataset coverage, but does not itself create an `AVAILABLE` observation.

## Historical versus live

Market-composite lending data may support research only after source approval. Live order authorization requires broker-specific evidence and later broker/account gates.

## Borrow costs

For each explicit accrual interval:

`borrow_fee_usd = EOD_short_market_value × annual_fee_rate / 360 × calendar_days`

The base scenario multiplier is 1x. The frozen Phase 01 pessimistic scenario is 2x.

The caller supplies accrual days because the exact broker settlement/accrual-start convention must be validated rather than inferred.

## Recall proxy

A data-source transition from `AVAILABLE` to `UNAVAILABLE` can generate a conservative `AVAILABILITY_WITHDRAWN` event. This event is not labeled a broker recall.

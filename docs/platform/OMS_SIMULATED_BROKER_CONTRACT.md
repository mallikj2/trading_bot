# OMS + SimulatedBroker Contract — P02-PF06

**Status:** Approved implementation contract  
**Phase:** 02B pre-purchase platform foundation  
**Authority:** Additive platform architecture only; does not change `CSMOM-LS-v0.2`.

## Purpose

Provide a deterministic order-management domain and a network-free broker simulator so later simulation, recovery, reporting, and reconciliation work use a realistic order lifecycle without connecting to a live broker.

## Hard boundaries

- `SimulatedBroker` is the only broker implementation allowed in PF06.
- Network I/O is disabled.
- No Schwab API, credentials, OAuth, broker account mutation, or live order submission is permitted.
- PF06 is not deployed paper trading and does not authorize Phase 03.
- Strategy scores, thresholds, universe rules, and alpha logic are unchanged.

## Order intent

An `OrderIntent` is immutable and content-addressed. It records:

- source `TradeLead` ID and content hash;
- stable instrument identity and display symbol;
- side and purpose;
- whole-share quantity;
- order type and time-in-force;
- strategy/version/decision provenance;
- creation timestamp;
- optional limit price.

Opening mappings:

- LONG → `BUY`
- SHORT → `SELL_SHORT`

Reduction mappings:

- LONG → `SELL`
- SHORT → `BUY_TO_COVER`

An increase-exposure order requires a `PLANNED` TradeLead. A reduction order requires an `ENTERED` or `EXIT_PENDING` TradeLead.

## Lifecycle

```text
CREATED
  → RISK_APPROVED
  → SUBMITTING
  → SUBMITTED
      ├→ ACKNOWLEDGED → PARTIALLY_FILLED → FILLED
      ├→ REJECTED
      ├→ CANCEL_PENDING → CANCELED
      ├→ EXPIRED
      └→ UNKNOWN → RECONCILING → broker-confirmed state
```

Invalid transitions fail closed.

## UNKNOWN policy

`UNKNOWN` means the client cannot prove whether the venue accepted, rejected, filled, or canceled the order.

Mandatory policy:

```text
UNKNOWN → RECONCILING
```

Blind resubmission is prohibited. This prevents duplicate positions after network/response uncertainty.

## Fill accounting

Each fill has a unique execution ID, whole-share quantity, positive price, and aware timestamp.

The projector rejects:

- duplicate execution IDs;
- overfills;
- a `FILLED` event whose cumulative quantity is not exactly the requested quantity;
- a `PARTIALLY_FILLED` event that does not represent a true partial quantity.

Average fill price is quantity-weighted from immutable fill records.

## Runtime-safety integration

PF04 permissions are authoritative:

| Runtime state | Increase exposure | Reduce exposure | Cancel known open orders |
|---|---:|---:|---:|
| ACTIVE | yes, simulation only | yes | yes |
| REDUCING | no | yes | yes |
| HALTED | no | no | yes |

`ACTIVE` never means live trading is authorized.

## Event journal integration

Every OMS fact is represented as a PF03 `DomainEvent` and must be appended before projection.

Event types include:

- `OMS.ORDER_CREATED`
- `OMS.ORDER_RISK_APPROVED`
- `OMS.ORDER_SUBMITTING`
- `OMS.ORDER_SUBMITTED`
- `OMS.ORDER_ACKNOWLEDGED`
- `OMS.ORDER_PARTIALLY_FILLED`
- `OMS.ORDER_FILLED`
- `OMS.ORDER_REJECTED`
- `OMS.ORDER_CANCEL_PENDING`
- `OMS.ORDER_CANCELED`
- `OMS.ORDER_EXPIRED`
- `OMS.ORDER_UNKNOWN`
- `OMS.ORDER_RECONCILING`

Replaying the append-only journal must reconstruct the same order-state hash after restart.

## Simulated broker truth

The simulator distinguishes client-visible outcome from broker truth. For example, the client may receive `UNKNOWN` while broker truth is `ACKNOWLEDGED` or `REJECTED`. Reconciliation reveals the deterministic simulated truth.

This is deliberate preparation for PF10 recovery/reconciliation without claiming real broker behavior.

## Acceptance criteria

PF06 passes only if automated tests demonstrate:

- deterministic intent identity and serialization;
- PLANNED TradeLead → order mapping;
- long/short open and close side mapping;
- acknowledged submission;
- partial fill then full fill;
- direct broker rejection;
- cancellation;
- expiration;
- unknown submission and unknown cancellation;
- no blind resubmission after `UNKNOWN`;
- reconciliation to acknowledged/rejected/canceled/fill state;
- duplicate execution and overfill rejection;
- PF04 ACTIVE/REDUCING/HALTED enforcement;
- PF03 restart/replay state-hash equivalence;
- simulated broker has no network/live capability.

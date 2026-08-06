# Data Contracts

## Status

**DRAFT — exact schemas and providers are Phase 2 deliverables.**

## Universal requirements

Every record must define:

- Source and source version where available
- Instrument identifier and symbol mapping
- Event timestamp
- Availability timestamp
- Ingestion timestamp
- Time zone semantics
- Adjustment status
- Validation status
- Data version or immutable object identifier

The system must distinguish the time an event occurred from the time it became available to the strategy.

## Core domain records

### Instrument

Required concepts: stable internal identifier, symbol history, exchange, asset type, currency, listing and delisting dates, trading status, and classification.

### Market bar

Required concepts: instrument, interval, bar start and end, availability timestamp, open, high, low, close, volume, trade count when available, adjustment metadata, and quality flags.

### Quote

Required concepts: bid, ask, sizes, event and availability timestamps, source, and quality flags.

### Corporate action

Required concepts: action type, effective date, announcement and availability timestamps, ratio or amount, currency, source, and revision history.

### Feature observation

Required concepts: feature name, version, instrument, observation timestamp, availability timestamp, value, null reason, source dependencies, transformation metadata, and leakage-test status.

### Signal

Required concepts: strategy version, signal identifier, instrument, decision timestamp, input-data version, direction, strength or rank, expiry, entry and exit semantics, and abstention reason.

### Risk decision

Required concepts: proposed intent, approved or rejected quantity, every evaluated limit, risk state, reason codes, portfolio snapshot version, and decision timestamp.

### Order intent and broker order

Required concepts: deterministic client order identifier, strategy and signal lineage, side, quantity, order type, limit or stop values, time in force, state, broker identifiers, acknowledgements, and transitions.

### Fill and position

Required concepts: broker source, order identifier, instrument, side, quantity, price, fees, event timestamp, settlement attributes where relevant, and reconciliation status.

## Data-quality behavior

Critical missing, stale, inconsistent, duplicated, non-finite, or unverifiable fields must produce an explicit quality event. No live feature, signal, risk, or order calculation may silently substitute a default for critical data.

## Storage rules

- Raw historical data is immutable.
- Normalized data and features are versioned derivatives.
- Corrections create new versions rather than overwriting evidence used by prior experiments.
- Research experiments record all data and feature versions.
- Production journals record the exact inputs used for every decision.

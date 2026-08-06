# System Architecture

## Status

**CONCEPTUAL — detailed architecture is a Phase 5 deliverable.**

This document records binding architectural direction without claiming implementation is complete.

## Logical flow

```text
Market / Fundamental / News Providers
                  |
                  v
           Data Adapter Layer
                  |
                  v
      Validation + Normalization
                  |
          +-------+-------+
          |               |
          v               v
    Raw Data Store   Data-Quality Monitor
          |
          v
    Feature Pipeline
          |
          v
    Strategy Engines
          |
          v
    Signal Aggregator
          |
          v
    Regime Controller
          |
          v
       Risk Engine
          |
          v
  Portfolio Constructor
          |
          v
   Execution Planner
          |
          v
    Broker Adapter
          |
          v
 Broker / Exchange Account
          |
          v
Order and Position Reconciler
          |
   +------+------+------+
   |             |      |
   v             v      v
State Store  Audit Log  Metrics / Alerts
```

## Architectural constraints

- Adapters isolate vendor and broker APIs from domain logic.
- Strategy output is an intent, never an order submission.
- The independent risk engine may reduce or reject intent.
- Execution is idempotent and reconciliation-aware.
- Broker state is authoritative for orders, fills, and positions.
- Research, backtest, paper, and live use separate configuration, credentials, databases, logs, and permissions.
- Raw data is immutable and separate from normalized data and features.
- Timestamps are stored in UTC internally.
- Money and quantity use decimal-safe semantics where required.
- Every production decision is reproducible from data version, code version, configuration, and recorded inputs.

## Candidate local stack

Selection is deferred until mandate and data requirements are approved. Candidate technologies include Python, NumPy, pandas or Polars, SciPy, statsmodels, scikit-learn, vectorbt for research, an event-driven simulator, DuckDB and Parquet for historical data, SQLite for lightweight operational state, SQLAlchemy and migrations, Pydantic settings, FastAPI, pytest, property-based testing, Ruff, static typing, and structured JSON logs.

No listed technology is approved merely by appearing here.

## Trust boundaries

1. External data providers
2. Broker API
3. Secret store and environment configuration
4. Local persistence
5. Strategy and feature packages
6. Risk engine
7. Execution service
8. Human control surface
9. Monitoring and alert channels

A failure in a non-critical alert channel must not make the trade path unsafe. A failure in critical validation, persistence, reconciliation, broker state, or risk state blocks new orders.

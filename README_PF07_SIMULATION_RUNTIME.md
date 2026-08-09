# PF07 Deterministic Simulation Runtime

PF07 adds a controlled local synthetic-session runner over the existing TradeLead, runtime-safety, event-journal, OMS, and SimulatedBroker layers.

Quick fixture execution from repository root:

```bash
PYTHONPATH=src python -m trading_bot.platform.simulation_cli \
  tests/fixtures/platform/pf07_two_order_plan.json \
  ./pf07_simulation.sqlite \
  --result ./pf07_result.json
```

This command performs no network I/O and cannot submit real orders.

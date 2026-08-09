# P02-PF10 Recovery + Reconciliation Simulation

PF10 adds deterministic crash/recovery and local-vs-simulated-broker reconciliation to the cumulative Phase 02 repository.

Primary implementation:

- `src/trading_bot/platform/recovery.py`
- `configs/platform/recovery_reconciliation.yaml`
- `tests/unit/platform/test_recovery.py`
- `tests/integration/platform/test_recovery_reconciliation_flow.py`
- `web/src/pages/RecoveryPage.tsx`

The implementation is network-free, uses no real broker, never blind-resubmits an uncertain order, and fails closed on unexplained divergence.

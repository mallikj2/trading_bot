# Project Roadmap

The phases are sequential. A later phase may be discussed for dependency awareness but may not be implemented prematurely.

| Phase | Name | Primary outcome | Current status |
|---:|---|---|---|
| 0 | Mandate Discovery | Approved feasible trading mandate | In progress |
| 1 | Strategy Research Specification | Falsifiable hypothesis, exact rules, baselines, pre-registered criteria | Not started |
| 2 | Data and Statistical Design | Point-in-time data contracts, universe, features, validation | Not started |
| 3 | Backtesting and Falsification | Vectorized and event-driven evidence, robustness and cost tests | Not started |
| 4 | Risk Management | Independent deterministic risk engine specification | Not started |
| 5 | Production Architecture | Typed modular architecture and persistence boundaries | Not started |
| 6 | Order and Broker Safety | Idempotent order lifecycle, reconciliation, execution controls | Not started |
| 7 | Reliability and Operations | Preflight, restart recovery, monitoring, kill switch | Not started |
| 8 | Journal, Analytics, Governance | Reproducible audit trail and periodic reporting | Not started |
| 9 | Paper-to-Live Gates | Evidence-based paper and tightly limited live progression | Not started |

## Cross-phase rules

- Record assumptions before testing.
- Freeze protected acceptance criteria before final evaluation.
- Preserve raw data and experiment history.
- Separate strategy intent, risk approval, execution submission, broker acceptance, and actual fills.
- Prefer rejection of weak ideas over defending them emotionally.
- A failed phase or strategy is a valid research result.

## Milestone definitions

### Research-ready

Phase 0 passes and the initial mandate is approved.

### Backtest-ready

Phases 1 and 2 pass; hypothesis, timing, universe, features, data contracts, and leakage controls are approved.

### Paper-ready

Phases 3 through 8 pass all applicable statistical, execution, risk, architecture, reconciliation, and operational gates.

### Limited-live-ready

Paper evidence satisfies Phase 9, no critical defects remain, and an explicit limited-live decision is recorded.

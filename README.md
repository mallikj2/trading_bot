# Professional Local Algorithmic Trading Platform

A research-first, safety-critical platform for developing, falsifying, paper trading, and—only after explicit gates—running limited live strategies for a personal US equities and ETF account.

## Current status

- Current phase: **Phase 0 — Mandate Discovery**
- Phase status: **IN PROGRESS**
- Permitted mode: **Research and documentation only**
- Paper trading: **Not yet permitted**
- Live trading: **Prohibited**

No strategy is presumed profitable. An attractive backtest is evidence for further investigation, not proof of an edge.

## Governing documents

- [`docs/governance/MASTER_SPECIFICATION.md`](docs/governance/MASTER_SPECIFICATION.md) — governing specification
- [`AGENTS.md`](AGENTS.md) — concise operating rules for Codex and coding agents
- [`docs/project/CURRENT_STATE.md`](docs/project/CURRENT_STATE.md) — authoritative active phase and blockers
- [`docs/project/DECISIONS.md`](docs/project/DECISIONS.md) — append-only decision register
- [`docs/project/ACCEPTANCE_CRITERIA.md`](docs/project/ACCEPTANCE_CRITERIA.md) — pre-registered gates
- [`docs/project/OPEN_RISKS.md`](docs/project/OPEN_RISKS.md) — unresolved risks
- [`docs/project/ROADMAP.md`](docs/project/ROADMAP.md) — sequential delivery plan

## Non-negotiable principles

1. Fail closed when critical state is uncertain.
2. Separate research, simulation, paper, and live environments.
3. Keep the live trade path deterministic and version controlled.
4. Prefer evidence and simple baselines before complexity.
5. Record assumptions, timestamps, versions, decisions, and state transitions.
6. Treat broker positions, orders, and fills as authoritative.
7. Never weaken acceptance criteria after seeing protected results.

## Documentation map

```text
docs/
├── governance/
│   ├── MASTER_SPECIFICATION.md
│   ├── TRADING_MANDATE.md
│   ├── RISK_POLICY.md
│   └── PAPER_TO_LIVE_GATES.md
├── project/
│   ├── CURRENT_STATE.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   ├── ACCEPTANCE_CRITERIA.md
│   ├── OPEN_RISKS.md
│   └── CHANGELOG.md
├── architecture/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATA_CONTRACTS.md
│   └── ADR/
│       ├── README.md
│       └── ADR-0001-DOCUMENTATION-AS-SYSTEM-OF-RECORD.md
└── phases/
    ├── PHASE_00_MANDATE_DISCOVERY.md
    ├── PHASE_01_STRATEGY_RESEARCH.md
    ├── PHASE_02_DATA_STATISTICAL_DESIGN.md
    ├── PHASE_03_BACKTESTING_FALSIFICATION.md
    ├── PHASE_04_RISK_MANAGEMENT.md
    ├── PHASE_05_PRODUCTION_ARCHITECTURE.md
    ├── PHASE_06_ORDER_BROKER_SAFETY.md
    ├── PHASE_07_RELIABILITY_OPERATIONS.md
    ├── PHASE_08_JOURNAL_GOVERNANCE.md
    └── PHASE_09_PAPER_TO_LIVE.md
```

## Workflow

1. Read `CURRENT_STATE.md` and the current phase document.
2. Resolve blockers and record decisions.
3. Freeze relevant acceptance criteria before protected evaluation.
4. Implement only the approved, current-phase scope.
5. Run and record actual validation.
6. End each phase with `PASS`, `CONDITIONAL PASS`, or `FAIL`.
7. Update project state before moving to the next phase.

## Important notice

This repository is engineering and research infrastructure, not investment advice. Live deployment is prohibited until every required historical, operational, broker, reconciliation, recovery, and limited-live gate is explicitly passed.

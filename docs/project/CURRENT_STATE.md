# Current Project State

## Project status

- Current phase: **Phase 0 — Mandate Discovery**
- Phase status: **IN PROGRESS**
- Trading mode allowed: **RESEARCH AND DOCUMENTATION ONLY**
- Historical backtesting allowed: **Not until Phase 1 specification is approved**
- Paper trading allowed: **NO**
- Live trading allowed: **NO**
- Last updated: **2026-08-05**
- Repository branch: **main**
- Repository commit: **To be recorded after documentation commit**

## Approved mandate

Not yet approved. See `docs/governance/TRADING_MANDATE.md`.

## Binding decisions

- The master specification is the governing project document.
- Development proceeds sequentially through defined phases.
- No strategy is presumed to generate alpha.
- Live decisions must remain deterministic and version controlled.
- Fail-closed behavior, reconciliation, and reproducibility have priority.

See `docs/project/DECISIONS.md` for the append-only register.

## Current objective

Complete mandate discovery, resolve feasibility conflicts, compare three initial mandates, select one mandate, and freeze its core operating and risk constraints.

## Phase entry criteria

- Governing specification stored in the repository
- Agent operating rules stored in `AGENTS.md`
- Project-state documents initialized
- Research, simulation, paper, and live separation accepted

## Phase exit criteria

- All critical mandate questions answered
- One initial mandate approved
- Account and broker constraints documented
- Universe, horizon, direction, overnight permission, and benchmark approved
- Initial risk tolerances approved
- Data budget and laptop uptime documented
- Human-approval model approved
- Feasibility conflicts and unresolved risks recorded

## Active tasks

1. Complete the twelve mandate-discovery decisions.
2. Compare end-of-day long-only, intraday liquid-equity, and daily/weekly long-short alternatives against actual constraints.
3. Approve one mandate and update the decision, risk, and acceptance registers.

## Blockers

- Starting account size unknown
- Cash versus margin account unknown
- Broker unknown
- Long-only versus long-short unknown
- Holding horizon unknown
- Overnight and weekend permissions unknown
- Portfolio drawdown tolerance unknown
- Daily loss limit unknown
- Risk-per-trade limit unknown
- Data budget unknown
- Human approval model unknown
- Laptop uptime and connectivity window unknown

## Prohibited work

- No broker credentials
- No order submission code
- No live or paper trader
- No strategy optimization
- No final acceptance thresholds derived from observed results
- No claims of expected profitability

## Phase decision

**CONDITIONAL PASS — repository governance is initialized, but mandate discovery is incomplete.**

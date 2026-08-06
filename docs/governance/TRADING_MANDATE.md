# Trading Mandate

## Status

**NOT APPROVED — Phase 0 mandate discovery is incomplete.**

This document becomes binding only after the required account, risk, operational, broker, data-budget, and human-approval decisions are recorded in `docs/project/DECISIONS.md`.

## Candidate recommendation

Unless mandate-discovery answers justify a more complex approach, the preferred initial candidate is:

- US-listed, highly liquid equities and broad-market ETFs
- Daily or end-of-day signal generation
- Long-only
- No leverage
- No options, penny stocks, or OTC securities
- Regular trading hours only
- Limited, reproducible, liquidity-screened universe
- Simple momentum or trend hypothesis as the first research candidate
- Conservative volatility- or stop-distance-based sizing
- Paper trading before any live activity
- Manual approval or daily arming during limited live validation

This is a candidate, not an approved strategy or assertion of profitability.

## Required mandate fields

| Field | Approved value | Status |
|---|---:|---|
| Starting account size | TBD | Open |
| Account type | TBD | Open |
| Broker | TBD | Open |
| Long/short permission | TBD | Open |
| Primary holding horizon | TBD | Open |
| Overnight permission | TBD | Open |
| Weekend permission | TBD | Open |
| Maximum portfolio drawdown | TBD | Open |
| Maximum daily loss | TBD | Open |
| Maximum risk per trade | TBD | Open |
| Monthly data budget | TBD | Open |
| Human approval model | TBD | Open |
| Laptop uptime window | TBD | Open |
| Eligible instruments | TBD | Open |
| Benchmark | TBD | Open |
| Maximum positions | TBD | Open |
| Maximum turnover | TBD | Open |
| Maximum gross exposure | TBD | Open |
| Maximum net exposure | TBD | Open |

## Prohibited by default

Until separately researched and approved:

- High-frequency trading
- Tick-level whole-market scanning
- Complex order-book prediction
- Unrestricted shorting
- Options strategies
- Aggressive leverage
- Full Kelly sizing
- Reinforcement learning
- Autonomous LLM live-trade decisions
- Dozens of simultaneous signals

## Approval record

- Decision ID: Not assigned
- Approved by: Not approved
- Approval date: Not approved
- Effective version: Not approved
- Superseded mandate: None

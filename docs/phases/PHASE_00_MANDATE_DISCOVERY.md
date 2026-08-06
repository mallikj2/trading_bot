# Phase 0 — Mandate Discovery

## Objective

Select a feasible initial trading mandate before strategy design or implementation.

## Required conflict analysis

Resolve conflicts among holding period, frequency, account size, data budget, laptop reliability, long/short requirements, fundamental versus intraday inputs, universe breadth, execution sophistication, return expectations, and drawdown tolerance.

## Required decisions

1. Approximate starting account size
2. Cash or margin account
3. Broker preference
4. Long-only or long-and-short
5. Intraday, swing, or position horizon
6. Overnight and weekend permissions
7. Maximum portfolio drawdown
8. Maximum daily loss
9. Maximum risk per trade
10. Monthly data budget
11. Human approval model
12. Laptop uptime and connectivity window

## Candidate mandates

### A. End-of-day long-only swing

- Lowest initial operational burden
- Daily adjusted bars and later point-in-time universe data
- No short borrow requirement
- Overnight gap risk
- Strongest default fit for a local laptop

### B. Intraday highly liquid equities

- Reliable real-time data and continuous session uptime
- High execution and recovery burden
- Sensitive to spreads, latency, rejects, and partial fills
- Capital and account restrictions may materially affect feasibility

### C. Daily or weekly long-short factors

- Point-in-time universe and fundamental data burden
- Borrow availability, fees, recalls, and margin requirements
- Requires strong diversification and neutrality controls
- Computationally feasible but statistically and operationally complex

## Default recommendation

Candidate A is preferred unless actual constraints strongly justify another mandate.

## Acceptance criteria

See `docs/project/ACCEPTANCE_CRITERIA.md`.

## Failure modes

- Selecting a mandate before account or operating constraints are known
- Choosing intraday trading without continuous uptime and reliable data
- Assuming short availability or broker features
- Setting risk limits from desired returns rather than loss tolerance
- Using free development data as production-quality evidence

## Decision record

No mandate has been approved.

## Next three tasks

1. Answer all twelve mandate questions.
2. Record the comparison and selected mandate.
3. Update trading mandate, risk limits, open risks, and current state.

## Phase result

**CONDITIONAL PASS — governance is initialized; mandate decisions remain open.**

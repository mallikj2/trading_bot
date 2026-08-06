# Risk Policy

## Status

**DRAFT — binding thresholds are not yet approved.**

The independent risk engine has final authority to reduce or reject strategy-generated order intents. A strategy may request risk; it may not bypass this policy.

## Core rules

1. No new risk when broker and local state disagree.
2. No new risk when market data, calendars, configuration, persistence, or risk calculations are stale or unverifiable.
3. No discretionary averaging down.
4. Correlated positions are treated as combined risk.
5. Stops limit planned loss but do not eliminate gap or liquidity risk.
6. Risk limits may not be overridden to recover losses.
7. Position sizing must be deterministic and reproducible.
8. Full Kelly sizing is prohibited.

## Initial sizing model

```text
risk_budget = account_equity × configured_risk_fraction
per_share_risk = abs(entry_price - protective_exit_price)
raw_quantity = floor(risk_budget / per_share_risk)
approved_quantity = min(raw_quantity, all portfolio and execution caps)
```

Quantity must also satisfy:

- Maximum position percentage
- Buying-power constraints
- Maximum average daily volume participation
- Sector and industry limits
- Correlation limits
- Gross and net exposure limits
- Overnight and gap-risk limits
- Open-order exposure limits
- Broker rules
- Stress-loss limits

A zero, negative, missing, stale, or non-finite input produces rejection, not a fallback quantity.

## Risk states

- `NORMAL`
- `REDUCED_RISK`
- `NO_NEW_POSITIONS`
- `EXIT_ONLY`
- `HALTED`
- `MANUAL_REVIEW_REQUIRED`

State transitions may be triggered by daily loss, drawdown, abnormal volatility, data failure, broker mismatch, repeated rejection, unexpected slippage, model drift, or failed reconciliation.

## Threshold register

| Limit | Value | Status |
|---|---:|---|
| Maximum risk per trade | TBD | Open |
| Maximum single-name exposure | TBD | Open |
| Maximum sector exposure | TBD | Open |
| Maximum gross exposure | TBD | Open |
| Maximum net exposure | TBD | Open |
| Maximum overnight exposure | TBD | Open |
| Maximum open-order exposure | TBD | Open |
| Maximum daily loss | TBD | Open |
| Maximum weekly loss | TBD | Open |
| Maximum peak-to-trough drawdown | TBD | Open |
| Maximum consecutive execution errors | TBD | Open |
| Maximum volume participation | TBD | Open |
| Maximum acceptable spread | TBD | Open |

## Stop and exit hierarchy

1. Operational emergency action
2. Portfolio-risk liquidation or reduction
3. Protective stop
4. Strategy invalidation exit
5. Time stop
6. Trailing exit
7. Profit-taking rule

The exact precedence and conflict resolution must be specified before implementation.

## Exceptions

There are no silent exceptions. Any human override must be explicit, authenticated, time stamped, reason coded, and recorded without changing the historical strategy definition.

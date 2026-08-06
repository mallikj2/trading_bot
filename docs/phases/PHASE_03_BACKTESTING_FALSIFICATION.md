# Phase 3 — Backtesting and Falsification

## Status

**NOT STARTED — blocked by Phases 0 through 2.**

## Objective

Attempt to reject the strategy through chronological simulation, realistic costs, protected validation, multiple-testing controls, regime tests, ablations, and stability analysis.

## Required layers

1. Vectorized research backtester for rapid signal analysis
2. Event-driven simulator for chronological portfolio, order, and execution behavior

## Validation requirements

- Expanding or rolling walk-forward analysis
- Purging and embargo where labels overlap
- Nested selection where appropriate
- Untouched final out-of-sample period
- Complete experiment and parameter history
- Bootstrap and block-bootstrap uncertainty
- Entry-delay, increased-cost, best-trade-removal, regime, and parameter-neighborhood tests

## Cost and fill requirements

Model spread, commission, fees, slippage, impact approximation, volume participation, partial fills, cancellation, rejection, delay, gaps, and short-specific costs where relevant. A limit order is not filled merely because a bar touches the price.

## Exit gate

Issue `PASS`, `CONDITIONAL PASS`, or `FAIL` against criteria frozen before the final protected test. Failure is a valid result.

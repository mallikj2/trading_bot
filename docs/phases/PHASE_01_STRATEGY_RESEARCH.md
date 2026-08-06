# Phase 1 — Strategy Research Specification

## Status

**NOT STARTED — blocked by Phase 0.**

## Objective

Produce a falsifiable strategy specification without claiming an edge.

## Required outputs

- Economic or behavioral hypothesis and persistence rationale
- Exact eligible universe, horizon, frequency, direction, capacity, and benchmark
- Mathematical signal definitions with availability timestamps
- Entry, exit, expiry, missing-data, and interaction rules
- Explicit do-not-trade conditions
- Simple and randomized baselines
- Pre-registered performance, risk, turnover, stability, and benchmark criteria

## Required baselines

- Buy-and-hold benchmark
- Equal-weight universe
- Simple momentum
- Mean reversion when applicable
- Randomized or shuffled signal control
- Strategy without regime filtering
- Strategy without each major feature

## Key failure modes

- Vague, non-falsifiable hypothesis
- Feature timestamp later than decision timestamp
- Post-hoc universe or rule selection
- Complex model without simple incremental value
- Acceptance criteria set after observing protected results

## Exit gate

A complete specification and frozen acceptance criteria are required before Phase 2 or backtest implementation.

# Phase 2 — Data and Statistical Design

## Status

**NOT STARTED — blocked by Phases 0 and 1.**

## Objective

Define development, research, and live data tiers; protect point-in-time integrity; construct a reproducible universe; and specify versioned feature contracts.

## Required outputs

- Provider requirements and documented limitations
- Historical membership, delistings, symbol changes, mergers, splits, dividends, spinoffs, and filing/news availability handling
- Exchange calendar and daylight-saving policy
- Universe rules and survivorship limitations
- Immutable raw storage and versioned derived data
- Feature name, version, formula, source, frequency, availability, null, winsorization, scaling, expected range, unit test, and leakage test

## Key failure modes

- Using current constituents historically
- Using restated fundamentals without point-in-time timestamps
- Silent corporate-action errors
- Overwriting raw data
- Treating development data as production reliable
- Using event dates rather than information-availability timestamps

## Exit gate

No backtest may be treated as decision evidence until required data contracts and leakage controls pass.

# Validation Results — Phase 02 Revision-Aware Historical Earnings

**Date:** 2026-08-06  
**Task gate:** IMPLEMENTATION PASS / SOURCE CONDITIONAL

## Test execution

Full cumulative repository overlay:

```text
143 passed, 12 subtests passed in 6.58s
```

Focused earnings schedule suite:

```text
24 passed in 0.06s
```

The cumulative suite includes the approved Phase 01 strategy tests and all prior Phase 02 kernel, provider-adapter, historical-sector, and corporate-action/total-return tests contained in this cumulative overlay.

## Static and configuration validation

- Python compilation: PASS (`src` and `tests`)
- YAML parse: PASS — 7 configuration files
- JSON parse: PASS — 3 JSON fixture/result files
- Earnings adversarial fixture parse: PASS
- No credentials or proprietary earnings files embedded: PASS

## Earnings-specific behaviors verified

- Future schedule revisions are invisible to earlier decisions.
- Later decisions see only revisions whose `available_at` has passed.
- Empty event results without forward coverage block entry.
- Forward coverage shorter than the 10-session hold interval blocks entry.
- Earnings inside the minimum-hold interval block entry.
- Events outside that interval do not block entry when coverage is complete.
- Withdrawn dates remain unresolved rather than becoming false no-event states.
- BMO, unknown, and during-session events map to prior-session exits.
- AMC maps to the event-session exit.
- Weekend unknown-time events map conservatively to the prior trading session.
- Invalid AMC-on-non-session records fail closed.
- Late BMO/time revisions do not backdate exits; they emit operational exceptions and next-window exits.
- Duplicate revision keys fail closed.
- Mixed-provider coverage histories fail closed.
- Provider availability cannot postdate local ingestion in an impossible direction.
- A later revision can change a later decision while preserving the earlier historical decision.

## Evidence boundary

No credentialed Wall Street Horizon historical sample was available in this environment. Therefore this validation does **not** claim provider completeness, provider accuracy, retention rights, price, delivery schema, or full-universe historical coverage.

## Remaining external gate

Before the historical earnings source can be approved for the final acceptance backtest:

1. obtain a WSH historical DateBreaks + Earnings Date Daily Snapshots sample;
2. run `EARNINGS_PROVIDER_TRIAL_RUNBOOK.md`;
3. validate stable identity, timestamps, BMO/AMC/unknown encoding, withdrawals, and coverage;
4. approve local/raw/derived/post-termination retention terms.

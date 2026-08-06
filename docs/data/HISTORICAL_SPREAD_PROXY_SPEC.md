# Historical Spread Proxy Candidate

> **Model ID:** `CORWIN_SCHULTZ_CONSERVATIVE_V0_1`  
> **Status:** Candidate only — calibration pending  
> **Use:** Historical entry filter when observed quote history is unavailable

## 1. Purpose

Phase 01 requires blocking entries when the final historical spread estimate exceeds 35 basis points. The Massive Developer plan does not include historical NBBO quotes. Therefore a modeled value is allowed only if preregistered and clearly labeled as modeled.

## 2. Input contract

For session `t` and prior session `t-1`:

- raw high and low;
- valid, positive, non-suspect bars;
- no unresolved split or capital action in the two-session interval;
- both bars available by the decision timestamp.

## 3. Estimator

Use the Corwin-Schultz high-low estimator:

```text
beta  = ln(H[t]/L[t])^2 + ln(H[t-1]/L[t-1])^2
gamma = ln(max(H[t], H[t-1]) / min(L[t], L[t-1]))^2
alpha = (sqrt(2*beta) - sqrt(beta)) / (3 - 2*sqrt(2))
        - sqrt(gamma / (3 - 2*sqrt(2)))
raw_spread = 2 * (exp(max(alpha, 0)) - 1) / (1 + exp(max(alpha, 0)))
```

Candidate conservative output:

```text
spread_bps = max(5, 10_000 * raw_spread)
```

The five-basis-point floor is a preregistered conservative floor, not a measured quote.

## 4. Entry decision

```text
missing/invalid/model-not-calibrated -> BLOCK
spread_bps > 35 -> BLOCK
spread_bps <= 35 -> PASS only after calibration gate
```

## 5. Calibration gate

Before Phase 03 final acceptance, compare the model with observed consolidated quotes on a representative sample:

- at least 100 sessions;
- at least 200 securities across liquidity deciles;
- sampling around the intended 10:00–10:30 window;
- corporate-action and halt exclusions documented.

The model passes only if:

1. false-negative rate for actual spread above 35 bps is no more than 5%;
2. at least 95% of modeled values are finite and reproducible;
3. model error and rejection rates are reported by liquidity decile;
4. no parameter is adjusted after seeing strategy performance;
5. any calibration change creates a new model version.

Until this gate passes, the model may be used for engineering tests only.

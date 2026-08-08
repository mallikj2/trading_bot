# Core Market-Data Stack Representative Trial Runbook

**Version:** 0.2  
**Date:** 2026-08-08  
**Status:** Ready; external credentials/data not present in this validation environment

## 1. Environment

```bash
export KIBOT_USERNAME='...'
export KIBOT_PASSWORD='...'
export KIBOT_PRIVATE_RESEARCH_LICENSE_APPROVED=true
export DATABENTO_API_KEY='...'
export DATABENTO_RESEARCH_LICENSE_APPROVED=true
export DATABENTO_US_EQUITIES_DATASET='...'  # confirm exact dataset from the approved account; do not guess
export SEC_USER_AGENT='QuantTradingBot/0.2 monitored-contact@example.com'
```

Never commit credentials. Runtime acknowledgement flags do not create license rights; they record that the operator is running inside a separately approved scope. `DATABENTO_RESEARCH_LICENSE_APPROVED` must remain false until account/terms review is complete.

## 2. Preflight

```bash
PYTHONPATH=src python -m trading_bot.data.adapters.core_trial environment-status
```

## 3. Kibot price/archive trial

At minimum validate:

- unadjusted daily OHLCV for AAPL, META/FB history, C, TSLA, and five delisted liquid names;
- daily history across two early-close dates;
- immutable CSV persistence and secret redaction;
- adjustment endpoint schema for five splits/reverse splits and five dividends;
- response corrections create new snapshots rather than overwriting prior snapshots;
- a known ticker-reuse case is detected and **not** treated as a single instrument;
- the current active/delisted symbol list is never used as a historical membership list.

No Kibot symbol is promoted to `instrument_id` solely from its ticker.

## 4. Point-in-time security-master companion trial

Preferred candidate: Databento.

Required evidence:

- at least 10 calendar years of point-in-time coverage;
- listing and delisting dates;
- security type sufficient to isolate common stock and exclude ETFs/other issues;
- historical symbol mapping that preserves ticker changes and ticker reuse;
- stable identifiers usable to map into the local instrument master;
- retrieval/retention/private quantitative-use rights accepted for the chosen account.

Representative identity cases must include FB→META and at least one reused ticker. The trial runner uses the Databento SDK lazily; the approved SDK version must be pinned in the environment used for the credentialed run.

## 5. Exact execution-VWAP trial

For at least 20 liquid and 10 lower-liquidity names across normal and early-close sessions:

1. retrieve trade-level data for the next-session 10:00:00 inclusive to 10:30:00 exclusive ET window;
2. exclude invalid/non-regular prints according to the frozen execution-data contract;
3. calculate size-weighted trade VWAP;
4. verify incomplete/zero-trade windows produce `NO_FILL`;
5. immutably retain raw inputs and manifest hashes.

An OHLC approximation may not pass this gate.

## 6. Cross-provider reconciliation

For overlapping sessions:

- reconcile Kibot unadjusted daily OHLCV against the execution/reference source;
- investigate rather than silently average discrepancies;
- record provider correction/revision behavior;
- confirm corporate-action discontinuities against the Phase 02 action engine.

## 7. Pass conditions

`PASS` requires all of:

- Kibot paid entitlement observed;
- Kibot private-use/retention scope still unchanged;
- representative daily/delisted cases pass;
- PIT identity/listing source licensed and trialed;
- exact VWAP source licensed and trialed;
- raw snapshots retained immutably;
- no ticker-only identity inference;
- no current-state universe backfill;
- no unresolved schema ambiguity in acceptance-critical fields.

Until then, Phase 03 remains unauthorized.

# Historical Quote Source Evaluation

**Date:** 2026-08-06  
**Purpose:** Calibrate the Phase 01 35 bps modeled-spread gate without look-ahead and without violating market-data rights.

## Decision summary

No historical quote provider is approved yet. The calibration engine is provider-independent. A source may be used only after its executed terms permit internal non-display strategy research, local immutable archival, derived-model retention, and continued use for the approved research purpose after the relevant subscription or download window ends.

| Candidate | Historical quote evidence | Licensing / budget evidence | Decision |
|---|---|---|---|
| Massive Stocks Advanced | Public quote documentation exposes NBBO bid/ask, sizes, participant/SIP timestamps and long quote history. | USD 199/month exceeds the recurring USD 80 ceiling. More importantly, Massive's public Individual Market Data Terms state that market data is display-only absent another agreement, prohibit non-display / investment-strategy derivative use unless licensed, and require deletion on termination. | **REJECT under public individual terms for this research use.** Reconsider only with separate written non-display/research and retention rights. |
| Databento historical | Databento documents BBO/CBBO/MBP-1 style schemas, usage-based historical access and API timestamp semantics. | Public licensing guidance states historical T+1 data generally does not require an exchange license, and historical access is usage-based. Exact US-equities dataset coverage, cost, and account-specific retention terms still require a trial/contract review. | **Candidate #1 for evaluation**, not approved. |
| Cboe DataShop Equity & ETF Quotes / Trades | Cboe DataShop documents U.S. equity/ETF data from 2010-present with bid/ask or NBBO fields; historical one-time purchases are supported. | Exact historical panel price and permitted internal archival/non-display research rights must be confirmed for the selected purchase type. | **Candidate #2**, not approved. |
| Daily high/low proxy only | No extra source required. | Fits budget. | Insufficient alone. Corwin-Schultz remains a predictor, never an observed-spread substitute. |

## Governance correction: Massive

The earlier proposal to purchase one month of Massive Advanced, download a quote panel, cancel/downgrade, and continue retaining the data is **withdrawn**. Under the public Individual Market Data Terms reviewed on 2026-08-06, that workflow is not acceptable for this project unless Massive supplies a separate written agreement that expressly authorizes the intended non-display research and retention.

This is a project governance interpretation of the public terms, not legal advice. The Massive adapter remains in the codebase as a tested provider adapter, but use for research is disabled until the required license is recorded.

## Why observed quotes are calibration data, not direct signal inputs

The strategy decision occurs after the prior session close; the fill benchmark occurs the following session. Using that future quote stream to decide whether the prior-close candidate passes the 35 bps filter would be look-ahead bias.

Observed quotes therefore serve only as:

1. historical calibration targets for models fit using observations that are already historical at fit time;
2. ex-post execution-quality diagnostics;
3. later paper/live model validation.

## Source-approval acceptance criteria

Before any provider is used:

- exact dataset and history must cover the pre-registered calibration period;
- quote semantics must be sufficiently close to NBBO for the target definition;
- timestamps must permit deterministic window reconstruction;
- internal non-display algorithmic research must be permitted;
- local raw archival and immutable hashes must be permitted;
- post-termination/post-download research retention must be explicitly understood;
- one-time or usage cost must be approved;
- external redistribution is not required by this project and remains prohibited unless separately licensed.

## Official evidence reviewed

- Massive Market Data Terms of Service, last updated 2025-08-28.
- Massive stock quotes and pricing documentation.
- Databento pricing, historical API, licensing guidance, and BBO schema documentation.
- Cboe DataShop Equity & ETF Trades / Quotes product pages.
- Corwin & Schultz, *A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices*.

# Provider License Governance Correction

**Date:** 2026-08-06  
**Scope:** Phase 02 research market-data providers

## Finding

The project previously treated Massive Developer/Advanced as technically promising research-provider candidates, pending a later retention review. The current public Massive Individual Market Data Terms materially change that assessment.

Based on the public terms reviewed on 2026-08-06:

- the default license is personal/non-business/non-commercial;
- market data is display-use only unless a separate agreement says otherwise;
- non-display use and creation of an investment strategy from market data require licensing;
- termination/restriction/suspension requires cessation of use and deletion of market data.

Therefore the public individual terms are not an acceptable authorization basis for this local algorithmic-research platform's research archive or for the proposed post-cancellation historical quote retention.

## Governance action

1. No Massive credentialed research trial may be run solely because an API key is available.
2. The trial runner additionally requires an explicit `MASSIVE_RESEARCH_LICENSE_APPROVED=true` flag after written terms are reviewed.
3. Previously written Massive provider capability decisions are now interpreted as **technical capability only, not usage authorization**.
4. No existing raw Massive market data should be committed to the repository.
5. If separate written terms are obtained, they must be reviewed against internal non-display research, immutable local archival, derived-model retention, and termination/deletion obligations before the flag is enabled.

This is a project governance interpretation and not legal advice.

## Alternative-source direction

- Databento historical usage-based data: next candidate, pending dataset-specific coverage/cost and account-specific rights. Public guidance states historical T+1 data generally does not require exchange licensing.
- Cboe DataShop Equity & ETF Quotes/Trades: secondary candidate; product pages document 2010-present historical bid/ask/NBBO information and historical purchasing, but exact pricing and rights require review.

No alternative is approved by this correction alone.

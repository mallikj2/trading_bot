# Historical Short-Borrow Provider Trial Runbook

## Goal

Prove that the candidate dataset can support `CSMOM-LS-v0.2` without look-ahead and with reproducible retained evidence.

## Pre-trial legal gate

Do not download paid historical data until all are documented:

- permitted non-display quantitative research use;
- local raw-data retention period;
- derived-result rights;
- cancellation/termination obligations;
- redistribution restrictions;
- machine/API access rights.

## Representative cases

The credentialed sample must cover at least:

1. ordinary easy-to-borrow large-cap stock;
2. known hard-to-borrow stock;
3. high borrow-fee episode;
4. availability moving from positive to zero/unavailable;
5. delisted security;
6. ticker rename;
7. ticker reuse;
8. corporate-action period;
9. weekend/holiday carry interval;
10. a security with missing source data.

## Required validations

For every sample row confirm:

- stable instrument mapping;
- provider date/time semantics;
- when the observation became knowable;
- fee representation and annualization;
- availability units and aggregation methodology;
- missing-row semantics;
- revision/correction behavior;
- historical retention rights;
- snapshot reproducibility.

## Coverage report

For the intended backtest interval report by month:

- candidate short decisions;
- decisions with valid availability evidence;
- decisions with fee evidence;
- decisions with quantity evidence;
- unknown/missing percentage;
- HTB percentage;
- fee distribution;
- availability-withdrawal transitions;
- affected delisted/ticker-changed securities.

The final acceptance backtest cannot start until the coverage criteria are frozen and passed.

## Live Schwab trial

Separately, using a non-production test workflow where possible, record actual Schwab API/account outputs for:

- margin and short permission;
- symbol shortability;
- hard-to-borrow state;
- quoted borrow rate;
- available quantity if exposed;
- locate/confirmation behavior;
- rejection behavior when borrow disappears;
- reconciliation/statement evidence.

No short order is authorized merely by successful market-data retrieval.

# Financing Source Evaluation

**Reviewed:** 2026-08-06

## FRED / Board of Governors — DTB3

**Use:** optional cash-opportunity attribution only.  
**Decision:** APPROVED FOR REFERENCE USE.

FRED identifies DTB3 as the daily 3-Month Treasury Bill Secondary Market Rate, Discount Basis, sourced from the Federal Reserve Board H.15 release. The series is tagged `Public Domain: Citation Requested`; FRED's legal notice permits internal commercial use of public-domain/citation-requested series with attribution.

It is not the actual Schwab cash sweep yield and must not be represented as one.

## Charles Schwab Cash Features

**Use:** live account cash semantics.  
**Decision:** CURRENT CONTRACT EVIDENCE; HISTORICAL RATE SERIES NOT APPROVED.

Schwab states that Cash Feature rates can change daily. Its disclosure also excludes credit balances designated as collateral for obligations, including cash resulting from a short sale, from Free Credit Balance.

This supports restricted short-collateral accounting but does not provide a historical cash-rate series suitable for backfilling.

## Charles Schwab Margin Debit Rates

**Use:** current deployment guardrail only.  
**Decision:** NOT A HISTORICAL BACKTEST SERIES.

As reviewed on 2026-08-06, Schwab reports an 11.825% effective margin rate for debit balances below USD 25,000, with a 10.00% base rate last changed 2025-12-12. Schwab also states margin interest is calculated daily.

The initial limited-live mandate prohibits margin borrowing, so historical Schwab margin-rate reconstruction is not required for Phase 03 so long as the strategy remains at or below 1.0 gross leverage with no settled debit. Any debit encountered fails closed.

## Decision

No external financing source is a blocker to the primary Phase 01 acceptance return series because primary cash carry is frozen at zero and margin debit is prohibited. Optional cash-drag attribution may use DTB3; current Schwab rate evidence is deployment-only.

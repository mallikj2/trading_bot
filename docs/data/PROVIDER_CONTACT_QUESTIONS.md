# Provider Contact Questions — Phase 02C

Use these questions before setting any provider's `*_RESEARCH_LICENSE_APPROVED=true` flag. Answers should be retained as account/license evidence, not copied into source control if they contain confidential commercial terms.

## Databento

1. For a personal/private local quantitative-research project, may historical data downloaded under our account be retained indefinitely in an immutable private archive after a subscription or entitlement ends?
2. May the retained data be used indefinitely for internal non-display backtesting/reproducibility with no external redistribution?
3. Which Security Master plan/entitlement provides **full US-listed historical coverage**, including delisted listings, rather than a 1,000-symbol allocation? Please quote it.
4. Confirm the exact historical start date for the PIT Security Master fields we require: stable security/listing IDs, CIK, listing/delisting status, exchange, symbol changes, `ts_record`, and `ts_effective` (or equivalents).
5. Which historical US equities dataset/schema should be used to construct the project's next-session **10:00–10:30 ET market-wide trade VWAP**? Does it include the relevant FINRA TRF/off-exchange prints, and what venues/conditions must be filtered?
6. Which historical quote schema is appropriate for observed NBBO/spread calibration? What is its exact coverage history?
7. Can historical downloads and their exact license/entitlement metadata be independently hashed and retained for audit/reproducibility?
8. For PIT corporate actions, confirm start date, revision timestamps, cancellation/replacement representation, and whether the source includes complex events such as spinoffs, cash+stock mergers, delistings/liquidations, and outturn/successor identifiers.

## Kibot

The current public license now explicitly permits permanent private retention of delivered data after cancellation. Before purchase, confirm only operational details:

1. Does the $14/month EOD plan allow downloading the full available US stock EOD archive required by our private local research project during an active month?
2. Are unadjusted, split-adjusted, and fully adjusted stock histories all included in the EOD plan?
3. What files identify delisted/inactive stocks and historical ticker changes, and what known limitations exist around ticker reuse/renames?
4. Are corrections/backfills versioned or otherwise identifiable so our immutable raw snapshots can record when a historical file changes?

## Wall Street Horizon

1. Please provide a no-cost trial/sample of **DateBreaks plus historical/as-of snapshots** sufficient to reconstruct what earnings date/time information was known on each historical decision date.
2. What is the earliest historical date for earnings date revisions/confirmations and daily snapshots?
3. Does the feed preserve every prior schedule version, including confirmation/revision/withdrawal and BMO/AMC/time-of-day changes?
4. What field represents the timestamp at which each revision became available to clients?
5. Can a private research client retain delivered historical data indefinitely for backtest reproducibility after the contract ends?
6. Is internal non-display strategy research permitted? External redistribution is not required.
7. Please quote the smallest license/package that supplies the required US equities history and revision trail.

## Exchange Data International (EDI)

1. Please provide a free trial/sample covering the project's corporate-action golden cases: NVDA 2024 split, GE 2021 reverse split, IBM/Kyndryl spinoff, Xilinx/AMD stock acquisition, Twitter cash acquisition, and Bed Bath & Beyond terminal/zero-recovery event.
2. Confirm historical coverage dates for US equity corporate actions and all revision/change timestamps.
3. Confirm support for splits/reverse splits, cash/stock dividends, spinoffs, stock/cash+stock mergers, cancellations/revisions, delistings, liquidation/bankruptcy outcomes, successor instruments and outturn terms.
4. Your public site advertises perpetual ownership rights. Please confirm that our client agreement permits indefinite private retention/use of delivered data after cancellation for reproducible internal research.
5. Please quote only the US-equity fields/history required for the above use case, not a broader enterprise package.

## S3 Partners / AWS Data Exchange

1. The public AWS listing is technically suitable and free, but the standard AWS DSA requires removal after termination. Can S3 issue a **private/custom offer or written amendment** permitting indefinite private retention of already-delivered historical data after the subscription ends?
2. Is internal non-display quantitative research/backtesting permitted?
3. Does the PIT history since 2015 preserve all prior revisions and security identifiers exactly as known on each business date?
4. Are `Offer Rate`, `Bid Rate`, `Last Rate`, `IndicativeAvailability`, utilization, and available/lendable quantities all available historically for US equities?
5. What timestamps distinguish observation/effective/publication availability, and can the data support a fail-closed `available_at <= decision_at` model?
6. Are recalls/withdrawals/restrictions or equivalent availability changes represented historically?

## S&P Global Securities Finance / DataLend fallback

1. Quote the smallest US-equity historical package that provides PIT borrow availability/supply and fee/rate evidence suitable for private backtesting.
2. Confirm exact historical start dates and point-in-time/revision semantics.
3. Confirm whether historical data can be retained indefinitely after contract termination for reproducibility.
4. Identify fields for fee/rate, lendable/available quantity, utilization, availability/shortability and recall/restriction events.
5. Confirm internal non-display research permission and no requirement for external redistribution rights.

## Cboe DataShop fallback

1. Quote an all-US-equities historical sample/panel sufficient for spread calibration from 2010 onward.
2. Confirm whether Equity & ETF Quotes bid/ask values represent NBBO or product-specific quote snapshots, and define the construction methodology.
3. If exact trade-level benchmark verification is needed, quote Equity & ETF Trades with trade condition, venue, bid and ask fields.
4. Confirm private historical retention and internal non-display backtesting rights for purchased files.

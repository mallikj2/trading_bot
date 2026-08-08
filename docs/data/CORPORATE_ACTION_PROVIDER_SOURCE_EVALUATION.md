# Corporate-Action Provider Source Evaluation

**Date:** 2026-08-08  
**Phase:** 02 — Data and Point-in-Time Design  
**Gate:** P02-G09

## Requirement

The approved Phase 01 acceptance backtest requires at least ten calendar years where valid point-in-time data permit. The corporate-action source must therefore preserve historical event economics, revisions/cancellations, effective dates, and stable security identity for enough of that horizon to rebuild total returns without using future knowledge.

## Decision

### Preferred long-history source: Exchange Data International (EDI)

EDI Worldwide Corporate Actions is the preferred source to take into a negotiated representative trial.

Public evidence supporting the selection:

- EDI exposes a `GetHistoricalCorporateActions` API with listing/security/issuer identifiers, event IDs, record-action state, record-change timestamps, event creation timestamps, effective dates, event codes and related event links.
- EDI's security-reference material states that it has collected global corporate-action information since January 2003 and retains old/new values, effective dates and reasons for changes in historical event tables.
- EDI publicly advertises flexible licensing and perpetual-ownership options, but also states that agreements are client-specific.

This is strong enough to select EDI for the paid/trial gate, but **not** to declare the project's actual license approved. The executed order/agreement must explicitly permit the planned private quantitative use and retained immutable research snapshots.

### Preferred PIT overlap source: Databento Corporate Actions

Databento is selected as the independent point-in-time overlap source because it documents listing-level records, 60+ event types, retained delisted/relisted security continuity and a `pit=True` revision history. Public documentation places corporate-action history from 2018-05-01 to present.

That makes Databento valuable for revision/cancellation cross-checks and the recent representative cases, but **insufficient by itself** for the Phase 01 ten-calendar-year minimum.

### Kibot role: price-adjustment corroboration only

Kibot remains useful for simple split/dividend adjustment sanity checks and raw-versus-adjusted price continuity. It is not accepted as the complex corporate-action event master because its adjustment interface is centered on splits/dividends and it is already prohibited from serving as the historical identity authority.

### Official issuer / SEC / exchange evidence

Official sources are used as economic golden references for a finite representative panel. They validate that the licensed vendor describes the correct economics; they do not replace a historical provider feed for the full backtest.

## Representative panel

| Case | Economic behavior under test |
|---|---|
| NVDA 2024 | 10-for-1 forward split |
| GE 2021 | 1-for-8 reverse split |
| IBM/Kyndryl 2021 | 1 Kyndryl share per 5 IBM shares |
| Xilinx/AMD 2022 | 1.7234 AMD shares per Xilinx share |
| Twitter 2022 | USD 54.20 cash merger |
| Bed Bath & Beyond 2023 | equity cancellation with zero consideration |

The official-source case definitions live in `tests/fixtures/data/corporate_action_provider_golden_cases.json`.

## Rejected shortcuts

The following cannot close P02-G09:

1. Checking only provider-adjusted closing prices.
2. Using the current/latest corporate-action record without revision timestamps.
3. Matching only by ticker.
4. Treating an absent vendor event as zero consideration.
5. Using Databento's 2018+ history alone as proof for a ten-year acceptance period.
6. Inferring spinoff or merger successor identity from ticker text.

## Gate decision

**SOURCE SELECTION PASS / PROVIDER RECONCILIATION BLOCKED**

EDI + Databento is the selected trial architecture. P02-G09 remains BLOCKED until the licensed representative data are obtained, retained under approved terms, normalized, and all mandatory cases reconcile without unresolved ambiguity.

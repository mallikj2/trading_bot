# DECISIONS — Phase 02 Historical Short-Borrow Append

**Date:** 2026-08-06

## D02-BORROW-01 — Missing historical borrow is never free or available

**Decision:** A missing, expired, unknown, or unapproved borrow observation blocks a historical short decision.

**Rationale:** Phase 01 explicitly prohibits treating missing borrow evidence as free and available.

## D02-BORROW-02 — Research market-composite evidence cannot authorize live shorts

**Decision:** Historical market-composite lending data may support research after source approval, but live shorts require broker-specific current evidence.

**Rationale:** Regulation SHO locate obligations and actual broker inventory/fees are broker-specific.

## D02-BORROW-03 — Borrow cost remains decomposed

**Decision:** Stock-borrow fees are modeled separately from spread/slippage, commissions/regulatory fees, financing, and dividend/distribution liabilities.

**Rationale:** This preserves attribution and prevents double counting.

## D02-BORROW-04 — Borrow accrual formula uses explicit EOD value/rate/calendar days

**Decision:** Borrow fee is calculated as EOD short market value × annual quoted rate / 360 × explicit calendar days.

**Rationale:** This matches Schwab's published rate formula while avoiding an invented historical settlement/accrual-start rule.

## D02-BORROW-05 — Availability withdrawal forces a research exit

**Decision:** A point-in-time source transition from AVAILABLE to UNAVAILABLE derives an `AVAILABILITY_WITHDRAWN` event and requires exit at the next permitted window.

**Rationale:** It is conservative and observable without falsely calling the event an actual broker recall.

## D02-BORROW-06 — ORTEX standard consumer terms are not approved for canonical retained research data

**Decision:** ORTEX may be schema-tested, but paid research ingestion requires separate written research/retention approval.

**Rationale:** Standard consumer terms prohibit persistent independent archival and require deletion after termination, conflicting with immutable raw snapshots and reproducibility.

## D02-BORROW-07 — S&P Global Securities Finance is the preferred technical source candidate

**Decision:** Seek a representative sample and commercial/retention quote from S&P Global first, with DataLend/EquiLend as the secondary institutional candidate.

**Rationale:** Public product material most closely matches the required historical availability, fee, and recall-risk contract.

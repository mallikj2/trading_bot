# Phase 02 — Historical Earnings Schedule Source Evaluation

**Evaluation date:** 2026-08-06  
**Requirement:** preserve historical earnings schedules, timing classes, confirmations, changes, and the timestamp at which each version became known.

## Decision summary

**Preferred source for the final acceptance backtest:** Wall Street Horizon direct historical **DateBreaks** plus **Earnings Date Daily Snapshots**, pending a credentialed sample and retention-license approval.

No source is approved merely from public documentation.

## 1. Wall Street Horizon direct

### Documented strengths

Wall Street Horizon states that:

- DateBreaks delivers timestamped alerts for earnings-date confirmations and revisions;
- historical offerings include an audit trail of earnings-date changes;
- Daily Snapshots provide archived views of the earnings calendar as of a specific historical date;
- the company archives data as it publishes it;
- historical corporate-event data are available from 2006-present, with timeframe varying by dataset;
- its 2023 historical-data expansion described 17 years of DateBreaks, Earnings Date Daily Snapshots, and conference-call history.

Public earnings pages also expose expected timing such as Before Market and After Market and distinguish confirmed from unconfirmed/forecast dates.

### Why two historical products are preferred

`DateBreaks` provides the change/audit stream. `Earnings Date Daily Snapshots` provide state anchors for arbitrary historical dates. Together they allow the project to prove both:

1. what the calendar state was on a historical decision date; and
2. when a later date/time/status revision became known.

### Open items

Public documentation is not enough to approve the source. The trial must verify:

- exact machine-readable schema;
- stable issuer/security identifiers;
- timezone and timestamp precision;
- BMO/AMC/unknown/during-session encoding;
- withdrawals/cancellations;
- preliminary earnings handling;
- coverage universe and delisted-company history;
- local archival and post-termination retention rights;
- price and delivery method.

**Status:** `PREFERRED_PENDING_TRIAL_AND_LICENSE`

## 2. Massive / Benzinga Earnings

Massive's Benzinga Earnings API documents:

- historical and upcoming earnings records;
- `date`;
- `time`;
- `date_status` (`projected` / `confirmed`);
- `last_updated`;
- history advertised back to 2011;
- an individual Benzinga Earnings expansion priced at $99/month as of this evaluation.

However, the public endpoint contract does not establish that *prior versions* of the same scheduled event remain queryable after an update. A `last_updated` timestamp on the current record is not equivalent to a revision audit trail.

Massive/Benzinga therefore remains useful for development and cross-provider corroboration but is not approved as the sole point-in-time history source unless a credentialed trial proves immutable prior-version retrieval.

**Status:** `NOT_APPROVED_AS_SOLE_PIT_HISTORY`

## 3. Intrinio Corporate Events

Intrinio's Corporate Events product identifies Wall Street Horizon as its source and exposes earnings dates. Its current product page explicitly states **History: Most recent data only** and Enterprise access.

That does not satisfy the requirement to reconstruct what a historical strategy knew before later schedule changes.

**Status:** `REJECTED_AS_SOLE_HISTORICAL_SOURCE`

## 4. SEC filings and company press releases

SEC filing acceptance timestamps and press releases can corroborate realized or company-confirmed events. They are valuable audit evidence.

They are not a sufficient sole source because the strategy needs a complete forward calendar, including forecast/tentative states and revisions that may be published on company websites or collected before an SEC filing exists.

**Status:** `CORROBORATION_ONLY`

## 5. Acceptance ranking

| Source | Historical as-published state | Revision timestamps | Timing class | Forward forecasts | Publicly proven prior versions | Initial decision |
|---|---:|---:|---:|---:|---:|---|
| WSH DateBreaks + Daily Snapshots | Yes, documented | Yes, documented | Documented at product/calendar level | Yes | Yes, documented audit/snapshots | **Preferred / conditional** |
| Massive/Benzinga Earnings | Historical events | `last_updated` | Exact time field | Projected + confirmed | **Not proven** | Dev/corroboration |
| Intrinio Corporate Events | No; most recent only | Current metadata | Yes | Yes | No | Reject as sole source |
| SEC / company releases | Partial | Source publication timestamps | Sometimes | Incomplete | N/A | Corroboration |

## 6. Source-approval gate

The preferred source becomes `APPROVED` only after:

- representative-case trial passes;
- all admitted backtest instrument-decisions can prove forward earnings coverage;
- revision timestamps reproduce historical schedule states without future leakage;
- identity mapping is deterministic;
- local immutable storage is contractually allowed;
- post-termination retention/deletion terms are documented;
- internal research/backtest and derived-result rights are approved.

Until then, Phase 02 remains active and the final acceptance backtest cannot claim point-in-time earnings integrity.

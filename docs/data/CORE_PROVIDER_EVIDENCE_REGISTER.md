# Core Provider Evidence Register

**Reviewed:** 2026-08-08

| Evidence | Finding | Gate impact |
|---|---|---|
| Kibot license agreement | Private use granted; archival copies allowed; already-delivered data may be retained permanently after cancellation | P02-G05 PASS for personal/private scope |
| Kibot EOD subscription page | $14/30 days; up to 64 years EOD; unadjusted/split-adjusted/fully adjusted variants; EOD API | Supports low-cost EOD archive candidate |
| Kibot ticker-change/delisting docs | Renames rewrite symbol histories; ticker reuse concatenates unrelated issuers; thin delisted coverage may be incomplete | Kibot prohibited as sole PIT security master |
| Kibot format docs | Daily and minute CSV schemas documented; minute timestamps are bar-open; 1-minute OHLCV contains no exact bar VWAP | Exact acceptance VWAP needs trades or equivalent |
| Kibot all-stocks tick page | Tick data with listed/delisted coverage exists but current all-stocks package is high cost | Technically viable, not preferred budget path |
| Databento security-master docs | PIT security master with listing/delisting/security type and historical identifiers | Preferred identity companion candidate |
| Databento symbology docs | Historical symbols preserved as originally observed; ticker reuse supported by date/instrument mapping | Fits PIT identity requirement |
| Databento historical pricing/docs | Usage-based T+1 historical access is offered; reference/security-master docs permit internal display/non-display use, but project retention/account terms still require approval | Preferred trial path; P02-G18 remains BLOCKED |

## Decision boundary

Documentation evidence is sufficient to approve Kibot's **license scope** for this project, but not sufficient to claim data quality, completeness, credential entitlement, or representative-case coverage. Those remain empirical trial requirements.

# Phase 02 Provider Capability Matrix

**Version:** 0.1  
**Date:** 2026-08-05

Legend:

- `PASS-DOC`: official documentation explicitly supports the requirement.
- `PARTIAL`: some fields or history are present but the complete data contract is not established.
- `FAIL`: documented product does not support the requirement.
- `UNKNOWN`: no authoritative evidence was found; credentialed test or vendor confirmation required.

| Requirement | Massive Developer | SEC EDGAR | Norgate Platinum | Tiingo Power | WSH DateBreaks |
|---|---|---|---|---|---|
| Monthly cost/equivalent | USD 79 | Free | USD 52.50 annualized | USD 30 | Quote required |
| Ten-year EOD | PASS-DOC | FAIL | PASS-DOC | PASS-DOC | FAIL |
| Ten-year minute bars | PASS-DOC | FAIL | FAIL | PARTIAL | FAIL |
| PIT ticker list by date | PASS-DOC | PARTIAL | PASS-DOC via indicators | UNKNOWN | FAIL |
| Delisted securities | PASS-DOC | PARTIAL via filings | PASS-DOC | UNKNOWN | FAIL |
| Common-stock type | PASS-DOC | PARTIAL | PASS-DOC | UNKNOWN | FAIL |
| CIK/FIGI identity | PASS-DOC | CIK only | Provider identity | UNKNOWN | Vendor identity |
| Symbol changes | PARTIAL/experimental | PARTIAL | PASS-DOC operationally | UNKNOWN | FAIL |
| Mergers/spinoffs identity | PARTIAL | PARTIAL via filings | PARTIAL event indicators | UNKNOWN | Corporate events available separately |
| Raw OHLCV | PASS-DOC | FAIL | Original close/volume documented; raw OHLC must be tested | PASS-DOC | FAIL |
| Splits/dividends | PASS-DOC | Filing evidence only | PASS-DOC | PASS-DOC EOD actions | Events available separately |
| PIT market cap | FAIL until validated | PASS-DESIGN from filings | FAIL: current fundamentals | Fundamentals add-on/unknown PIT | FAIL |
| PIT sector | FAIL until validated | PASS-DESIGN using filing SIC | FAIL: current metadata not accepted as PIT | UNKNOWN | FAIL |
| Earnings date/time | FAIL | Actual filing only | FAIL | FAIL | PASS-DOC |
| Earnings revisions known-at | FAIL | FAIL | FAIL | FAIL | PASS-DOC |
| Historical NBBO quotes | Advanced plan, not Developer | FAIL | FAIL | IEX/consolidated limits | FAIL |
| Historical borrow | FAIL | FAIL | FAIL | FAIL | FAIL |
| Immutable local export | Flat files/API; license test pending | PASS | Proprietary DB and lapse risk | API; license test pending | Contract dependent |

## Decision summary

1. **Massive Developer** is the primary integrated price/reference/intraday trial because it alone fits the USD 80 ceiling while documenting ten years of minute aggregates.
2. **SEC EDGAR** is the point-in-time enrichment method for shares outstanding and SIC.
3. **WSH DateBreaks** is the only reviewed source explicitly documenting timestamped earnings-date revisions; price and historical sample remain unresolved.
4. **Norgate Platinum** is retained as a cross-validation option, especially for survivorship and major-exchange history, but cannot satisfy the VWAP requirement alone.
5. **Tiingo** is useful for engineering and live/reference checks, but IEX-only historical volume is not accepted as the final full-market VWAP benchmark; the consolidated equity endpoint is beta and needs a separate production/history validation.

# Provider Evidence Register

**Retrieved:** 2026-08-05  
**Purpose:** Trace every documentation-level provider claim used by the Phase 02 proof of concept.

Documentation evidence establishes only advertised capability. It does not replace credentialed response tests, coverage tests, or a license review.

| Source | Official URL | Claims used | Evidence state |
|---|---|---|---|
| Massive Stocks plans | https://massive.com/stocks | Developer plan price, ten-year history, all US stock tickers, reference data, corporate actions, minute aggregates, flat files, trades; quotes reserved for Advanced | DOCUMENTED |
| Massive minute flat files | https://massive.com/docs/flat-files/stocks/minute-aggregates | Per-minute US-equity OHLCV, Developer ten-year access, daily S3 files | DOCUMENTED |
| Massive all tickers | https://massive.com/docs/rest/stocks/tickers/all-tickers | Historical `date` query, active status, security type, exchange and identity fields | DOCUMENTED |
| Massive custom bars | https://massive.com/docs/rest/stocks/aggregates/custom-bars | Configurable aggregate interval and raw-versus-adjusted request semantics | DOCUMENTED |
| Massive ticker events | https://massive.com/docs/rest/stocks/corporate-actions/ticker-events | Ticker-change event support; complete identity-event graph not established | PARTIAL |
| Massive splits | https://massive.com/docs/rest/stocks/corporate-actions/splits | Historical split records | DOCUMENTED |
| Massive dividends | https://massive.com/docs/rest/stocks/corporate-actions/dividends | Historical dividend records | DOCUMENTED |
| SEC EDGAR APIs | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | Submissions and company-facts APIs; filing/XBRL data without API key | DOCUMENTED |
| SEC fair-access guidance | https://www.sec.gov/about/webmaster-frequently-asked-questions | Declared user agent, request-rate and automated-access rules | DOCUMENTED |
| Wall Street Horizon earnings calendar | https://www.wallstreethorizon.com/earnings-calendar | Earnings event timing and DateBreaks revision product | DOCUMENTED |
| Wall Street Horizon DateBreaks | https://www.wallstreethorizon.com/news/DateBreaksV3 | Timestamped earnings-date confirmations and revisions | DOCUMENTED; SAMPLE/PRICE PENDING |
| Norgate stock packages | https://norgatedata.com/stockmarketpackages.php | Survivorship-aware package, delisted-history coverage and price | DOCUMENTED |
| Norgate data content | https://norgatedata.com/data-content-tables.php | Major-exchange history, original data fields and corporate actions | DOCUMENTED |
| Norgate access model | https://norgatedata.com/index.php/pricing/ | Windows-local database and subscription access model | DOCUMENTED |
| Norgate FAQ | https://norgatedata.com/data-package-faq.php | Fundamental-data limitations and operational behavior | DOCUMENTED |

## Evidence hierarchy

1. Official documentation: capability candidate only.
2. Credentialed raw response: endpoint and schema evidence.
3. Representative historical cases: coverage evidence.
4. Repeatable snapshots and hashes: reproducibility evidence.
5. Written license review: retention and intended-use evidence.

A provider contract receives `PASS` only after all applicable evidence levels are complete.

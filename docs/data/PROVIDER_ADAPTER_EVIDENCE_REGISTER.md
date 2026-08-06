# Provider Adapter Evidence Register

**Reviewed:** 2026-08-05

| Evidence | Official source | Design consequence |
|---|---|---|
| Massive All Tickers accepts a `date` point-in-time parameter and returns exchange, active state, CIK, Composite FIGI, Share-Class FIGI, delisting date, and last-updated time | Massive Stocks REST — All Tickers | Implement dated active/inactive snapshots; require credentialed historical-semantic proof before normalization |
| Massive custom aggregate bars support custom intervals and may omit intervals when no qualifying trades occur | Massive Stocks REST — Custom Bars / Stocks overview | Treat missing intervals as missing; never synthesize a VWAP bar |
| Massive provides current split and dividend endpoints with execution/ex dates and factors | Massive Stocks REST — Splits and Dividends | Implement conservative effective-date normalization and raw payload retention |
| Massive ticker events supports ticker changes but is experimental | Massive Stocks REST — Ticker Events | Implement strict schema handling; unsupported event types block |
| Massive ticker overview documents market cap and SIC fields for a dated ticker request | Massive Stocks REST — Ticker Overview | Code path exists but remains disabled pending credentialed historical-as-of evidence |
| SEC submissions and companyfacts APIs are public JSON APIs and are updated in real time with typical short processing delays | SEC EDGAR APIs | Join facts to filing acceptance timestamps and add a conservative processing buffer |
| SEC fair-access guidance limits automated access to no more than 10 requests per second | SEC Developer Resources | Require declared User-Agent and enforce <=10 requests/second |
| SEC companyfacts returns facts by accession/filing, while submissions provides filing history | SEC EDGAR APIs | Use accession as the join key for shares availability |
| SEC submissions top-level SIC is not documented as an effective-dated filing history | Inference from official submissions/companyfacts API schema | Prohibit historical sector emission from current SIC metadata |

## Official URLs

- https://massive.com/docs/rest/stocks/tickers/all-tickers
- https://massive.com/docs/rest/stocks
- https://massive.com/docs/rest/stocks/corporate-actions/splits
- https://massive.com/docs/rest/stocks/corporate-actions/dividends
- https://massive.com/docs/rest/stocks/corporate-actions/ticker-events
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/about/developer-resources

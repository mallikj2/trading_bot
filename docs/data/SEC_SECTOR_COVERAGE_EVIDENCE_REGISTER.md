# SEC Sector Coverage Evidence Register

**Date:** 2026-08-08

| Evidence | Relevance | Status |
|---|---|---|
| SEC Developer Resources | Daily indexes/archives and fair-access maximum | Verified |
| SEC EDGAR APIs page | Submissions API structure, older fragment files, bulk archives | Verified |
| SEC Accessing EDGAR Data | Daily-index semantics and post-acceptance correction/removal behavior | Verified |
| SEC Webmaster FAQ | Declared User-Agent requirement and typical 1–3 minute filing-publication lag | Verified |
| Existing modern filing-header fixture | Parser behavior | PASS |
| Existing legacy SGML filing-header fixture | Parser behavior | PASS |
| Offline full-crawl simulation | Daily index -> immutable filing -> PIT sector -> coverage | PASS |
| Real sector-blind PIT target ledger | Required denominator | BLOCKED / upstream provider evidence pending |
| Real monitored-contact SEC User-Agent | Required for automated crawl | NOT PROVIDED IN PROJECT RUNTIME |
| Full SEC crawl | 99% coverage evidence | NOT RUN |
| 25 original-archive sector-change reviews | PAC risk control | NOT RUN |

Official references:

- https://www.sec.gov/about/developer-resources
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- https://www.sec.gov/about/webmaster-frequently-asked-questions
- https://www.sec.gov/Archives/edgar/daily-index/
- https://www.sec.gov/Archives/edgar/Oldloads/

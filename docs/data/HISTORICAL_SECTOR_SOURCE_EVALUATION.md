# Historical Sector Source Evaluation

**Version:** 0.1  
**Date:** 2026-08-05

## Requirement

CSMOM-LS-v0.2 permits no more than two names from the same sector on either portfolio side. Historical research therefore requires a sector classification that was publicly knowable at each decision timestamp. A current classification copied backward is prohibited.

## Alternatives

| Candidate | Point-in-time evidence | Cost/operations | Decision |
|---|---|---|---|
| SEC submissions JSON top-level SIC | Current-state field only; no effective-dated sequence | Free and easy | Rejected for historical use |
| Massive dated ticker overview SIC | Endpoint accepts an as-of date, but field semantics remain credential-trial dependent | Existing proposed $79/month tier | Retained as corroboration only until tested |
| Commercial GICS/ICB history | Strong taxonomy when properly licensed | Additional cost and retention restrictions | Deferred |
| SEC complete-submission filing headers | Each filing header includes accession, exact acceptance timestamp, filer/subject CIK, and assigned SIC | Public source; local immutable snapshots required | Selected |

## Selected source

The raw SEC filing header is the authoritative historical observation. SEC documentation identifies `ASSIGNED-SIC` as an EDGAR company-data header field. The SEC also documents the complete-submission acceptance timestamp, and filing index pages display the SIC associated with the filer at that filing.

Official evidence:

- https://www.sec.gov/edgar/searchedgar/edgarzones.htm
- https://www.sec.gov/about/webmaster-frequently-asked-questions
- https://www.sec.gov/edgar/searchedgar/sampleheader.htm
- https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list

## Taxonomy choice

The project maps the four-digit SEC SIC to the frozen Fama–French 12-industry grouping.

Taxonomy identifier:

```text
FAMA_FRENCH_12_FROM_SEC_SIC
```

Version:

```text
FF12-SIC-2026-08-05-v1
```

The mapping is frozen in source code before Phase 03. It uses only the published SIC ranges; it does not download or backfill Fama–French portfolio membership. The Fama–French construction page confirms that the 12-industry portfolios are assigned from four-digit SIC codes.

Reference:

- https://mba.tuck.dartmouth.edu/pages/faculty/ken.French/Data_Library/det_12_ind_port.html

## Conservative semantics

A filing-time SIC observation becomes usable only at:

```text
available_at = EDGAR acceptance timestamp + configured processing buffer
```

The sector interval begins at `available_at`, not at an inferred earlier business-change date. This can recognize a real change late, but cannot recognize it early.

A later filing that maps to a different FF12 sector closes the prior interval. Repeated filings that remain inside the same FF12 sector do not create redundant intervals.

## Coverage limitation

The source design is approved, but full-universe coverage has not been measured because the environment lacks a compliant project SEC User-Agent. Before the Phase 02 final gate, a credentialed/compliant crawl must demonstrate adequate coverage for otherwise-eligible instrument-months and manually review representative sector changes.

## 2026-08-08 coverage-crawl hardening

The source decision remains SEC filing-header assigned SIC, but the collection architecture is hardened in two ways:

1. **As-published daily master indexes are the canonical filing inventory.** SEC documents that later post-acceptance removals are not rewritten into previous daily indexes. This avoids silently dropping a filing merely because it was removed later.
2. **Complete-submission availability uses a 3-minute buffer, not 1 minute.** SEC's current Webmaster FAQ says filings are often public within 1–3 minutes of the EDGAR timestamp. The upper end is used conservatively.

The real coverage denominator must come from a sector-blind PIT historical universe ledger. A current ticker/CIK list is not an acceptable substitute because it would reintroduce survivorship bias.

Residual PAC correction risk is controlled by manual comparison of at least 25 detected sector-change filings against original daily archive (`Oldloads`) evidence during the real acceptance crawl.

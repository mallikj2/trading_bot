# External Provider Procurement Decision — 2026-08-08

**Decision status:** REVIEW PASS; purchases require explicit manual approval.  
**Scope:** Seven external Phase 02 blockers only.

## Decision summary

The minimum-spend provider stack is:

```text
SEC EDGAR                    $0
Databento signup/credits     $0 initial
Kibot EOD                    $14 for one month (recommended after approval)
WSH trial/quote              $0 to request
EDI trial/quote              $0 to request
S3/AWS inquiry               $0 provider subscription; AWS infra may cost
```

Unknown/custom spend is deferred until a representative sample proves it is necessary and licensing terms fit the immutable research archive.

## Gate-to-provider map

| Gate | Primary path | Backup | Pass condition relevant to procurement |
|---|---|---|---|
| P02-G04 | Kibot EOD + SEC/Databento companion evidence as designed | Reassess only if Kibot trial fails | Credentialed representative trial, retained raw archive, manifests, coverage and reconciliation PASS. |
| P02-G07 | Databento full-US PIT security-master ledger + SEC EDGAR crawl | Equivalent PIT security master | Sector-blind PIT denominator exists; full coverage thresholds and manual sector-change reviews pass. |
| P02-G09 | EDI long-history CA + Databento recent PIT overlap + Kibot simple-event corroboration | Equivalent perpetual/retainable CA source | Golden complex actions/revisions reconcile without unresolved conflicts. |
| P02-G11 | Wall Street Horizon DateBreaks + historical snapshots | Equivalent revision-aware event source | Historical prior versions and forward-coverage evidence pass; retention/private-research rights approved. |
| P02-G13 | Databento historical trades/quotes | Cboe DataShop | Observed quote panel and prior-close spread calibration pass coverage/bucket tests. |
| P02-G15 | S3 Partners only if retention amendment obtained | S&P Global Securities Finance / DataLend | PIT borrow rates/availability with retainable research license and representative coverage pass. |
| P02-G18 | Databento PIT Security Master + selected execution dataset | Equivalent companion | Full-US PIT identity and exact 10:00–10:30 ET execution benchmark coverage proven and license approved. |

## Provider-specific decision details

### SEC EDGAR — use

Free public source. The SEC currently limits automated access to 10 requests/second and requests a declared User-Agent. The project keeps its crawler at 5 requests/second to leave operational margin. No paid account or API key is required.

### Databento — open an account first; no monthly market-data plan yet

Current public pricing offers usage-based historical data with no monthly subscription requirement and $125 in new-user credits. That is sufficient to begin representative execution/spread data trials without committing to a $199+ monthly plan.

Security Master is a separate entitlement concern. Its public page describes PIT status/identifier history, but the flexible Standard/Starter-style allocation begins at 1,000 symbols and additional symbols are charged/require support. A full US historical universe will exceed 1,000 symbols, so the project must get an exact full-US entitlement/quote before treating G18/G07 as financially solved.

The account must also confirm the exact retention/internal non-display rights for the datasets used. Public internal-use language is encouraging but does not replace account-specific agreements.

### Kibot EOD — recommended first paid item

Current EOD price: **$14/month**, with up to 64 years of EOD history, EOD API/FTP/download access, and adjusted/split-adjusted/unadjusted stock data.

More importantly, the current Kibot license explicitly permits archival copies and says already-delivered data may be kept permanently and privately used after cancellation/lapse/license termination. This resolves the earlier retention concern for this project.

Decision: purchase exactly one month only after explicit user approval, download/manifest the representative archive, test coverage/identity limitations, and cancel unless continuing updates are justified.

### Wall Street Horizon — trial before quote acceptance

DateBreaks is designed to capture timestamped earnings-date confirmations/revisions. The public site offers/has offered no-cost trials, but the production price and archive/retention rights are not public enough to approve now.

Decision: request sample history, daily/as-of snapshots, exact dates, delivery mechanism, and written retention/private-research terms before purchase.

### Exchange Data International — trial before quote acceptance

EDI's current site advertises free trials, customized datasets, flexible licensing, and perpetual ownership rights. It remains the preferred long-history complex-corporate-action candidate because the gate requires revisions/outturns and history beyond the recent Databento PIT overlap.

Decision: obtain a sample covering the Phase 02 golden cases and a client-specific quote/agreement. Marketing language alone does not set `EDI_RESEARCH_LICENSE_APPROVED=true`.

### S3 Partners — technically attractive, standard retention terms block gate

The AWS listing is free and says its daily securities-finance data is point-in-time since 2015, with PIT identifiers, offer/bid/last financing rates and indicative availability. It also exposes historical and future revisions.

However, AWS Data Exchange terms are provider-offer-specific, and the standard AWS DSA requires removal of data within 90 days after termination/expiration. That conflicts with this project's permanent immutable historical evidence archive.

Decision: contact S3 for a private offer/amendment granting perpetual internal retention of delivered historical data. If not granted, do not use the standard listing to close G15.

### S&P Global Securities Finance — institutional borrow fallback

Current S&P Global material describes 23 years of PIT history and decades of daily supply/demand/fee data. Pricing is custom. It remains the main fallback if S3 cannot grant retainable terms.

### ORTEX — standard plan rejected

Standard ORTEX API/Data Services terms prohibit a persistent independent archive and require deletion within 30 days after termination. The standard product may be useful for other contexts, but it is incompatible with the Phase 02 immutable borrow archive.

### Cboe DataShop — spread fallback

Cboe Equity & ETF Quotes provides bid/ask, VWAP and interval data from 2010-present, with cart-based pricing. This is a strong fallback if Databento cannot economically supply the required observed quote panel.

## Purchase boundary

This document is a recommendation, not a purchase authorization.

```text
PROCUREMENT_READY_FOR_MANUAL_APPROVAL = true
PROCUREMENT_AUTHORIZED = false
```

No credential should be committed to Git. Any account/API credentials later supplied belong in a local `.env`/secret store and are outside immutable research artifacts.

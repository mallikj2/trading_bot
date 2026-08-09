# Phase 02 — External Account & License Procurement Review

**Task:** `P02-PROCUREMENT-REVIEW`  
**Date:** 2026-08-08  
**Status:** **PASS**  
**Predecessor:** `P02-PF-GATE = PASS`  
**Next:** `P02-PROCUREMENT-AUTHORIZATION` — explicit user approval required before any paid purchase, subscription, credential entry, or vendor agreement acceptance.

## Objective

Refresh the remaining external Phase 02 provider choices against current public pricing, coverage, and license/retention terms; map each provider to the seven blocked Phase 02 gates; and define the lowest-cost evidence sequence without weakening any existing gate.

This review is a procurement decision record only. It does **not** authorize spending and does not mark any provider license flag approved.

## Existing gate state

The existing 18 mandatory Phase 02 data gates remain authoritative and unchanged:

```text
PASS         11
BLOCKED       7
CONDITIONAL   0
```

Remaining blockers:

1. `P02-G04` — core provider credentialed representative trial.
2. `P02-G07` — full historical-sector coverage crawl.
3. `P02-G09` — corporate-action provider reconciliation.
4. `P02-G11` — revision-aware earnings source sample/license.
5. `P02-G13` — observed-spread quote source/calibration.
6. `P02-G15` — historical borrow source/license/coverage trial.
7. `P02-G18` — PIT security-master/exact-execution companion trial.

## Procurement decisions

| Provider | Decision | Immediate provider cost | Primary gates | Reason |
|---|---|---:|---|---|
| SEC EDGAR | APPROVE no-cost configuration | $0 | G07 | Public/free; use declared User-Agent and conservative request rate. |
| Databento | APPROVE account/free-credit trial only | $0 initial | G18, G13, G09, G07 | Historical usage-based access and new-user credits reduce trial cost. Full-US Security Master entitlement/retention and exact execution coverage still require confirmation. |
| Kibot EOD | RECOMMEND one month after explicit approval | $14 | G04 | Low-cost retained EOD archive; current published license explicitly allows permanent private retention of delivered data. |
| Wall Street Horizon | REQUEST trial + quote | Unknown | G11 | DateBreaks is revision-aware; sample, exact historical coverage, and retention rights must be approved before gate closure. |
| Exchange Data International | REQUEST free trial + quote | Unknown | G09 | Long-history corporate-action candidate; public material advertises perpetual ownership, but client agreement controls. |
| S3 Partners via AWS Data Exchange | EVALUATE only; request retention amendment | $0 provider subscription; AWS costs possible | G15 | PIT securities-finance history since 2015 is attractive, but standard AWS DSA termination terms are incompatible with our permanent immutable archive unless amended. |
| S&P Global Securities Finance / DataLend | FALLBACK quote | Unknown | G15 | Institutional historical borrow fallback if retainable S3 terms cannot be obtained. |
| ORTEX standard API | REJECT for retained Phase 02 archive | $49+ / month | G15 | Standard terms prohibit persistent independent archive and require deletion after termination. |
| Cboe DataShop | FALLBACK only | Dynamic | G13 | Strong observed quote/trade history from 2010; use only if Databento does not satisfy calibration/coverage economics. |

## Minimum-spend sequence

The recommended sequence is deliberately staged so that expensive/custom vendors are not purchased before low/no-cost evidence is exhausted:

1. Configure compliant SEC EDGAR monitored-contact `User-Agent`; keep crawler at the project's conservative 5 requests/second ceiling.
2. Create a Databento account and use the $125 new-user historical credits; do **not** buy a monthly equities plan solely for the historical trial.
3. Ask Databento for the exact full-US PIT Security Master entitlement/quote and written confirmation of the account-specific internal-research/retention terms needed by this project.
4. After explicit user approval, purchase one month of Kibot EOD at $14 and run `P02-G04` representative archive trial.
5. Use Databento credits/usage-based historical access for exact-execution and observed-spread representative trials, and recent PIT corporate-action overlap.
6. Build the real sector-blind target ledger and run the full SEC sector coverage crawl.
7. Request a no-cost Wall Street Horizon DateBreaks/historical-snapshot trial and quote.
8. Request an EDI corporate-actions free trial and client-specific perpetual-use quote.
9. Ask S3 Partners for a private/custom AWS offer or written amendment permitting permanent internal retention of delivered historical data. Do not close G15 under the default 90-day deletion rule.
10. If S3 cannot supply retainable terms, request S&P Global Securities Finance and/or DataLend pricing/retention terms.
11. Use Cboe DataShop only if the Databento quote/spread calibration panel fails the gate.
12. Rerun all seven external gates and the final Phase 02 audit.

## Cost conclusion

The **known minimum initial provider cash outlay is $14**, consisting only of one month of Kibot EOD, if and when the user explicitly approves the procurement plan. Databento's public pricing currently offers $125 in new-user historical credits and usage-based historical data without a monthly subscription requirement; SEC is free; WSH/EDI can be approached for trials; and the S3 AWS listing is free of provider subscription charge, though AWS infrastructure charges may apply.

This is **not** a forecast of total Phase 02C cost. Full-US Databento Security Master, WSH, EDI, and a retainable borrow source may require later quoted spend.

## License conclusions that changed the plan

### Kibot

The earlier retention ambiguity is resolved by the current published Kibot license. It permits private archival copies and explicitly states that data already delivered may be kept and privately used after cancellation/lapse/termination. This makes one month of EOD a viable low-cost retained-core-data trial, subject to compliance with the private-use/no-redistribution limits.

### S3 Partners / AWS Data Exchange

The data itself is technically promising: the public listing says daily, global, point-in-time history since 2015 with PIT identifiers, financing rates, indicative availability, and historical revisions. The listing is free of provider subscription charge. However, the standard AWS Data Subscription Agreement says authorization ends at termination/expiration and requires removal of data within 90 days. Therefore it cannot close our immutable archive gate unless those terms are amended/customized.

### ORTEX

ORTEX remains unsuitable under its standard API/Data Service terms because those terms prohibit creating a persistent archive that remains usable after termination and require deletion within 30 days. It is therefore not an approved Phase 02 borrow archive purchase.

## Governance outcome

```text
P02-PROCUREMENT-REVIEW = PASS
P02-PF-GATE = PASS
PROCUREMENT_READY_FOR_MANUAL_APPROVAL = true
PROCUREMENT_AUTHORIZED = false
PHASE03_AUTHORIZED = false
STRATEGY_PROFITABILITY_VALIDATED = false
```

No external gate changes to PASS as a result of this review. A public marketing statement is not substituted for an executed/account-specific license where the gate requires one.

## Public-source snapshot used for this review

Accessed 2026-08-08:

- SEC, “Accessing EDGAR Data”: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- Databento pricing: https://databento.com/pricing
- Databento Security Master: https://databento.com/security-master
- Kibot subscriptions: https://www.kibot.com/subscribe.html
- Kibot License Agreement: https://www.kibot.com/license.html
- Wall Street Horizon DateBreaks/earnings information: https://www.wallstreethorizon.com/earnings-calendar
- EDI Corporate Actions: https://www.exchange-data.com/corporate-actions/
- S3 Partners AWS Marketplace listing: https://aws.amazon.com/marketplace/pp/prodview-gau2ek656qhwc
- AWS standard Data Subscription Agreement: https://aws-mp-standard-contracts.s3.amazonaws.com/Data-Subscription-Agreement-for-AWS-Marketplace-2022-07-14.pdf
- S&P Global Securities Finance: https://www.spglobal.com/market-intelligence/en/solutions/products/securities-finance
- ORTEX terms: https://public.ortex.com/terms-and-conditions/
- Cboe DataShop Equity & ETF Quotes: https://datashop.cboe.com/equity-etf-quotes

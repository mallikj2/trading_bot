# Transaction Fee Evidence Register

**Reviewed / frozen:** 2026-08-08  
**Status:** `P02-G17 PASS`

## Scope

This register freezes the official regulatory-equivalent sell-side fee basis used by Phase 03. It does not attempt to reproduce exact historical broker statement rounding or pass-through behavior.

## SEC Section 31 evidence

The authoritative index is the SEC **Fee Rate Advisories** page, which lists the named transaction-fee advisories used to reconstruct all effective intervals in `configs/data/regulatory_fee_basis.yaml`.

Official source:

- SEC, *Fee Rate Advisories*: https://www.sec.gov/rules-regulations/fee-rate-advisories
- SEC, *Section 31 Transaction Fees: Basic Information for Firms*: https://www.sec.gov/rules-regulations/fee-rate-advisories/section-31-transaction-fees-basic-information-firms

The frozen schedule uses the following effective rates:

| Effective interval | USD per million covered sales | Evidence family |
|---|---:|---|
| 2010-01-01 – 2010-01-14 | 25.70 | SEC FY2010 advisories |
| 2010-01-15 – 2010-03-31 | 12.70 | SEC FY2010 Advisory #4 |
| 2010-04-01 – 2011-01-20 | 16.90 | SEC FY2010 Advisory #5 / FY2011 continuation |
| 2011-01-21 – 2012-02-20 | 19.20 | SEC FY2011 Advisory #5 / FY2012 continuation |
| 2012-02-21 – 2012-03-31 | 18.00 | SEC FY2012 Advisory #5 |
| 2012-04-01 – 2013-05-24 | 22.40 | SEC FY2012 Advisory #6 / FY2013 continuation |
| 2013-05-25 – 2014-03-17 | 17.40 | SEC FY2013 Advisory #3 / FY2014 continuation |
| 2014-03-18 – 2015-02-13 | 22.10 | SEC FY2014 advisories / FY2015 continuation |
| 2015-02-14 – 2016-02-15 | 18.40 | SEC FY2015 advisories / FY2016 continuation |
| 2016-02-16 – 2017-07-03 | 21.80 | SEC FY2016 advisories / FY2017 continuation |
| 2017-07-04 – 2018-05-21 | 23.10 | SEC FY2017 Advisory #3 / FY2018 continuation |
| 2018-05-22 – 2019-04-15 | 13.00 | SEC FY2018 Advisory #3 / FY2019 continuation |
| 2019-04-16 – 2020-02-17 | 20.70 | SEC FY2019 Advisory #2 / FY2020 continuation |
| 2020-02-18 – 2021-02-24 | 22.10 | SEC FY2020 advisories / FY2021 continuation |
| 2021-02-25 – 2022-05-13 | 5.10 | SEC FY2021 advisories / FY2022 continuation |
| 2022-05-14 – 2023-02-26 | 22.90 | SEC FY2022 Advisory #2 / FY2023 continuation |
| 2023-02-27 – 2024-05-21 | 8.00 | SEC FY2023 advisories / FY2024 continuation |
| 2024-05-22 – 2025-05-13 | 27.80 | SEC FY2024 Advisory #2 / FY2025 continuation |
| 2025-05-14 – 2026-04-03 | 0.00 | SEC FY2025 Advisory / FY2026 continuation |
| 2026-04-04 – 2026-08-08 | 20.60 | SEC FY2026 Advisory |

Recent direct advisories:

- FY2025: https://www.sec.gov/rules-regulations/fee-rate-advisories/2025-2
- FY2026: https://www.sec.gov/rules-regulations/fee-rate-advisories/2026-2

## FINRA TAF evidence

Official sources include:

- FINRA Regulatory Notice 12-31: https://www.finra.org/rules-guidance/notices/12-31
- FINRA Trading Activity Fee FAQs: https://www.finra.org/rules-guidance/guidance/faqs/trading-activity-fee
- FINRA Fee Adjustment Schedule: https://www.finra.org/rules-guidance/rule-filings/sr-finra-2024-019/fee-adjustment-schedule
- SR-FINRA-2020-032 and predecessor notices identified in FINRA's rulemaking record.

Frozen equity TAF schedule:

| Effective interval | USD/share | Cap/trade |
|---|---:|---:|
| 2010-01-01 – 2011-06-30 | 0.000075 | 3.75 |
| 2011-07-01 – 2012-02-29 | 0.000090 | 4.50 |
| 2012-03-01 – 2012-06-30 | 0.000095 | 4.75 |
| 2012-07-01 – 2021-12-31 | 0.000119 | 5.95 |
| 2022-01-01 – 2022-12-31 | 0.000130 | 6.49 |
| 2023-01-01 – 2023-12-31 | 0.000145 | 7.27 |
| 2024-01-01 – 2025-12-31 | 0.000166 | 8.30 |
| 2026-01-01 – 2026-08-08 | 0.000195 | 9.79 |

FINRA Regulatory Notice 12-31 confirms the July 1, 2012 increase from USD 0.000095/share with a USD 4.75 cap to USD 0.000119/share with a USD 5.95 cap. FINRA's current adjustment schedule confirms 2024/2025 at USD 0.000166/share capped at USD 8.30 and 2026 at USD 0.000195/share capped at USD 9.79.

## Broker commission

Schwab's current online commission for listed stocks remains a deployment assumption outside P02-G17. It is not silently projected backward as a historical commission series by this gate.

## Stock borrow and financing

Stock-borrow fees and financing remain separate contracts. They must not be included in the regulatory-equivalent fee object.

## Acceptance decision

The official Section 31 and FINRA TAF history is sufficiently explicit, effective-dated, and contiguous for the frozen 2010-01-01 through 2026-08-08 interval.

`P02-G17 = PASS`

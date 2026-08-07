# Short-Borrow Evidence Register

**Reviewed:** 2026-08-06

| Evidence | Project implication |
|---|---|
| SEC Regulation SHO requires a locate/reasonable grounds before a broker-dealer effects a short sale and requires documented compliance. | Live shorting needs broker-specific authorization; public market data cannot substitute for the broker locate. |
| Schwab pricing guide: certain short positions may incur Stock Borrow Fees calculated from end-of-day short market value × quoted rate / 360; quoted rate may change daily. | Implement effective daily fee inputs and 360-day formula; never hard-code one rate. |
| S&P Global Securities Finance advertises 23 years point-in-time history, 20 years daily history, supply/demand/fee data, borrow availability, and recall/concentration risk. | Best technical historical source identified; commercial/retention terms still required. |
| DataLend describes current and historical securities-lending fees, utilization, on-loan and inventory balances, and transaction-level data. | Strong institutional alternative; commercial/retention terms still required. |
| ORTEX documents historical cost-to-borrow and short-availability APIs, historical ticker resolution, and daily borrowing data. | Technically promising and accessible for testing. |
| ORTEX API pricing lists Trader at USD 49/month and Quant at USD 149/month. | Trader fits the recurring USD 80/month target but may be credit-limited; Quant exceeds it. |
| ORTEX standard consumer terms prohibit a persistent independent database and require deletion after termination. | Standard consumer terms conflict with immutable raw research retention; source not approved absent separate terms. |
| IBKR Short Securities Availability exposes quantity, number of lenders, current indicative rate, and historical indicative borrow rates. | Useful broker-specific corroboration, but not canonical Schwab historical economics. |
| OCC public stock-loan volume/balance data describe cleared stock-loan activity. | Useful market stress evidence; not symbol-level broker availability/fee evidence. |

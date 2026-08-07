# Short-Borrow Historical Source Evaluation

**Date:** 2026-08-06

| Source | Historical fee | Historical availability | Recall / risk evidence | PIT identity | Retail/API access | Retention fit | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| S&P Global Securities Finance | Yes | Yes | Recall/concentration risk described | Requires contract validation | Institutional | Open | Preferred technical fit |
| DataLend / EquiLend | Yes | Inventory/utilization | Lending-market history and transaction data | Requires contract validation | Institutional | Open | Secondary institutional candidate |
| ORTEX API | Yes | Yes | Availability/FTD; not equivalent to actual broker recall | Historical ticker resolution documented | USD 49 Trader / USD 149 Quant | **Fails standard consumer raw-retention requirement** | Evaluation only unless custom terms |
| Interactive Brokers | Historical indicative rate | Current quantity/lenders; broker-specific | Broker-specific | Broker identity | Account tool | Not validated | Corroboration only |
| SEC / FINRA / OCC public data | No broker fee | No broker availability | Stress/crowding/fail indicators | Public identifiers vary | Public | Generally usable subject to source terms | Supplemental only |

## ORTEX licensing conclusion

ORTEX's standard consumer terms cover API/Data Services but prohibit a persistent independent database and require deletion after termination. The Phase 02 kernel requires immutable raw provider snapshots and reproducibility across future reruns. Those requirements conflict.

Therefore:

- the API may be schema-tested using the documented `TEST` key;
- paid research ingestion remains disabled unless separate written terms approve non-display quantitative research and long-term retention;
- `ORTEX_API_KEY` alone is not sufficient authorization;
- production use additionally requires `ORTEX_RESEARCH_LICENSE_APPROVED=true`.

## Recommended procurement order

1. Request a small historical equities securities-finance sample and research/retention quote from S&P Global.
2. Request an equivalent sample/quote from DataLend/EquiLend.
3. Ask ORTEX whether custom Data Services terms can permit immutable local retention; proceed only with written approval.
4. Keep IBKR and public regulatory data as corroborating/stress evidence, not canonical borrow availability.

# PIT Security-Master / Exact-Execution Evidence Register

**Reviewed:** 2026-08-08

| Evidence | Current finding | Project consequence |
|---|---|---|
| Databento Security Master schema | PIT records expose `ts_record`, `ts_effective`, listing/security/issuer identifiers and shares-outstanding fields | Adapter preserves both effective and knowledge timestamps; `ts_record` gates historical knowledge |
| Databento Security Master dataset specification | History is documented from 2005-01-01; listed and delisted securities remain tracked | Technically sufficient history for the Phase 01 ≥10-year acceptance horizon, subject to credentialed coverage trial |
| Databento Trades schema | Trade-level records expose event/receive timestamps, instrument ID, price, size and quality flags | Supports exact size-weighted execution-window calculations within the selected dataset |
| Databento US Equities Mini specification | Derived aggregate feed has a `trades` schema but anonymizes component venues | Presence of trade records does not by itself prove full market-wide execution coverage |
| Databento US equities coverage documentation | US equities are available through multiple venue/direct/composite datasets; off-exchange TRFs are material to volume | Final execution dataset requires a documented and approved historical coverage profile |
| Databento pricing/licensing portal | Historical access is usage-based and licensing is dataset/use-case dependent | Account-specific research/retention rights must be reviewed before P02-G18 PASS |

## Official references

- https://databento.com/docs/schemas-and-data-formats/security-master
- https://databento.com/docs/venues-and-datasets/security-master
- https://databento.com/docs/schemas-and-data-formats/trades
- https://databento.com/docs/venues-and-datasets/equs-mini
- https://databento.com/equities
- https://databento.com/pricing
- https://databento.com/docs/portal

## Evidence still required

- actual account license/retention approval;
- selected execution dataset and historical coverage statement;
- credentialed PIT representative panel;
- credentialed execution-window representative panel;
- generated sector-blind monthly target ledger;
- immutable raw snapshots and manifest hashes.

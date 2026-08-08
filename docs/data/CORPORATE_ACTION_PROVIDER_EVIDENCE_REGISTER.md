# Corporate-Action Provider Evidence Register

**Date:** 2026-08-08

| Evidence | Source | What it supports | Gate use |
|---|---|---|---|
| Historical corporate-action API | EDI Developer — `GetHistoricalCorporateActions` | Historical endpoint; event/listing IDs; record action/change timestamps; effective dates and event links | Long-history trial candidate |
| PIT/reference history | EDI Security Reference Data | Corporate-action/reference changes collected since Jan 2003; PIT security reference back to Jan 2005 | Ten-year horizon plausibility and identity support |
| Licensing statement | EDI corporate-actions site | Flexible licensing / perpetual-ownership options; client-specific agreements | Candidate only; executed agreement still required |
| Corporate-actions dataset | Databento | 60+ event types; listing-level PIT records; history from 2018-05-01; delisted/relisted continuity | Recent PIT overlap source |
| Event definitions | Databento | `FSPLT`, `RSPLT`, `DMRGR`/`SOFF`, `MRGR`, `BKRP`, `LIQ`, `LSTAT` semantics | Trial query/event mapping |
| Adjustments API | Kibot | Splits and dividends; simple price adjustment corroboration | Secondary sanity check only |
| NVDA 2024 split FAQ | NVIDIA Investor Relations | 10-for-1 split economics | Golden case |
| GE 2021 reverse split notice | GE | 1-for-8 reverse split economics | Golden case |
| IBM/Kyndryl distribution FAQ | IBM Investor Relations | 1 KD per 5 IBM distribution | Golden case |
| AMD/Xilinx completion filing | AMD / SEC | 1.7234 AMD shares per XLNX share | Golden case |
| Twitter merger 8-K | SEC | USD 54.20 per share cash consideration | Golden case |
| BBBY effective-plan 8-K | SEC | equity cancelled without consideration / no value | Golden case |

## Evidence boundary

The register records publicly documented capabilities and official golden economics. It does **not** claim that EDI or Databento paid data have been obtained in this environment, that the vendors are complete for the intended full universe, or that the executed license terms have been approved.

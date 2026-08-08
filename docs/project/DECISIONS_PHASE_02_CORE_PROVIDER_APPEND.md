# DECISIONS — Phase 02 Core Provider Append

**2026-08-08**

- **D02-CP01:** Select Kibot as the first paid core EOD price-archive candidate.
- **D02-CP02:** Approve Kibot public license for private personal retained research snapshots only; re-review for institutional/multi-user/commercial use.
- **D02-CP03:** Request and store Kibot raw prices as unadjusted; do not use provider back-adjusted history as canonical raw input.
- **D02-CP04:** Reject ticker as identity. Kibot ticker-renames and ticker-reuse behavior require independent PIT security-master evidence.
- **D02-CP05:** Prefer Databento for the next PIT security-master/exact-execution trial; no license or coverage approval is implied yet.
- **D02-CP06:** Add a distinct mandatory Phase 02 gate for PIT identity and exact execution evidence rather than hiding it inside the core EOD provider gate.
- **D02-CP07:** Final 10:00–10:30 ET acceptance VWAP must come from validated trades/equivalent exact data, not OHLC approximation.

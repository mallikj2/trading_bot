# DECISIONS — Phase 02 Regulatory Fee Basis Append

**2026-08-08**

- **D02-FEE-01:** Freeze the Phase 03 regulatory-equivalent fee basis from 2010-01-01 through 2026-08-08.
- **D02-FEE-02:** Select SEC Section 31 rates by historical trade date using the official Fee Rate Advisories; never backfill the current rate across history.
- **D02-FEE-03:** Select FINRA equity TAF rates and caps by historical trade date using official FINRA notices/rule filings.
- **D02-FEE-04:** Apply the FINRA low-price exemption when execution price per share is below the applicable per-share TAF rate.
- **D02-FEE-05:** Treat this schedule as a regulatory-equivalent research basis and do not claim exact historical Schwab customer invoice/pass-through or rounding replication.
- **D02-FEE-06:** Require the Phase 03 acceptance interval to be fully contained within the frozen fee interval; otherwise fail closed and extend/re-freeze the schedule before running.
- **D02-FEE-07:** Record fee schedule version and configuration hash with every Phase 03 acceptance run.
- **D02-FEE-08:** Promote `P02-G17 FULL_ACCEPTANCE_PERIOD_REGULATORY_FEE_BASIS` from CONDITIONAL to PASS.

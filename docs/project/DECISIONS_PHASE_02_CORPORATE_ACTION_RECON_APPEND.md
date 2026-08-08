# DECISIONS — Phase 02 Corporate-Action Provider Reconciliation Append

**2026-08-08**

- **D02-CA-R01:** Prefer EDI Worldwide Corporate Actions as the long-history provider candidate for P02-G09.
- **D02-CA-R02:** Prefer Databento Corporate Actions as an independent point-in-time overlap source; do not treat its 2018+ history as sufficient by itself for the ten-calendar-year Phase 01 acceptance horizon.
- **D02-CA-R03:** Kibot adjustments may corroborate splits/dividends but cannot serve as the complex corporate-action master.
- **D02-CA-R04:** Resolve provider revisions per stable provider event ID and reconciliation cut-off; future revisions are invisible.
- **D02-CA-R05:** Multiple distinct provider events matching the same action type/effective date are ambiguous and must block.
- **D02-CA-R06:** Spinoffs require an outturn identifier; stock mergers/acquisitions require a successor identifier; cash consideration requires matching currency.
- **D02-CA-R07:** Official issuer/SEC/exchange cases are economic golden references only and cannot substitute for licensed provider coverage.
- **D02-CA-R08:** Keep P02-G09 BLOCKED until the EDI long-history and Databento PIT-overlap representative trials pass under approved account/license terms.

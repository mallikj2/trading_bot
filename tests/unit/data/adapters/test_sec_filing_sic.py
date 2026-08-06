from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from uuid import uuid4

from trading_bot.data.adapters.http import ProviderRequestError
from trading_bot.data.adapters.sec_filing_sic import (
    SecArchivesClient,
    SecFilingHeaderError,
    build_sector_history,
    map_sic_to_ff12,
    parse_filing_sic,
    select_sector_as_of,
)
from trading_bot.data.errors import PointInTimeError

UTC = timezone.utc


TEXT_HEADER = """<SEC-DOCUMENT>0000320193-25-000001.txt : 20250201
<SEC-HEADER>0000320193-25-000001.hdr.sgml : 20250201
<ACCEPTANCE-DATETIME>20250201161530
ACCESSION NUMBER:               0000320193-25-000001
CONFORMED SUBMISSION TYPE:      10-Q
PUBLIC DOCUMENT COUNT:          1
FILED AS OF DATE:               20250201

FILER:

    COMPANY DATA:
        COMPANY CONFORMED NAME:          APPLE INC
        CENTRAL INDEX KEY:               0000320193
        STANDARD INDUSTRIAL CLASSIFICATION: ELECTRONIC COMPUTERS [3571]
        FISCAL YEAR END:                 0928

    FILING VALUES:
        FORM TYPE:                       10-Q

<DOCUMENT>
<TYPE>10-Q
fake body
"""

TEXT_HEADER_WITH_OTHER_ENTITY = """<SEC-DOCUMENT>0001104659-26-011958.txt : 20260209
<SEC-HEADER>0001104659-26-011958.hdr.sgml : 20260209
<ACCEPTANCE-DATETIME>20260209132403
ACCESSION NUMBER:               0001104659-26-011958
CONFORMED SUBMISSION TYPE:      SCHEDULE 13D/A

SUBJECT COMPANY:

    COMPANY DATA:
        COMPANY CONFORMED NAME:          Atlanta Braves Holdings, Inc.
        CENTRAL INDEX KEY:               0001958140
        STANDARD INDUSTRIAL CLASSIFICATION: SERVICES-AMUSEMENT & RECREATION SERVICES [7900]

    FILING VALUES:
        FORM TYPE:                       SCHEDULE 13D/A

FILED BY:

    COMPANY DATA:
        COMPANY CONFORMED NAME:          MALONE JOHN C
        CENTRAL INDEX KEY:               0000937797
        STANDARD INDUSTRIAL CLASSIFICATION: UNKNOWN SIC - 0000 [0000]

    FILING VALUES:
        FORM TYPE:                       SCHEDULE 13D/A
<DOCUMENT>
"""

LEGACY_HEADER = """<SEC-DOCUMENT>0000000011-99-000001.txt : 19990105
<SEC-HEADER>0000000011-99-000001.hdr.sgml : 19990105
<ACCEPTANCE-DATETIME>19990104103000
<ACCESSION-NUMBER>0000000011-99-000001
<TYPE>10-K
<FILER>
<COMPANY-DATA>
<CONFORMED-NAME>TEST ENERGY CO
<CIK>0000000011
<ASSIGNED-SIC>1311
</COMPANY-DATA>
</FILER>
</SEC-HEADER>
<DOCUMENT>
"""


class FakeTextTransport:
    def __init__(self, payload: str):
        self.payload = payload
        self.urls: list[str] = []

    def get_text(self, url, *, headers, timeout):
        self.urls.append(url)
        return self.payload


class SecFilingSicTests(unittest.TestCase):
    def test_archives_client_builds_pinned_complete_submission_path(self):
        transport = FakeTextTransport(TEXT_HEADER)
        client = SecArchivesClient(
            user_agent="quant-trading-bot owner@example.com",
            transport=transport,
            requests_per_second=10,
        )
        payload = client.complete_submission("0000320193", "0000320193-25-000001")
        self.assertEqual(payload, TEXT_HEADER)
        self.assertEqual(
            transport.urls[0],
            "https://www.sec.gov/Archives/edgar/data/320193/000032019325000001/0000320193-25-000001.txt",
        )
        with self.assertRaises(ProviderRequestError):
            client._http.get_text("https://example.com/escape")  # noqa: SLF001

    def test_parse_modern_header_uses_exact_acceptance_and_target_cik(self):
        observation = parse_filing_sic(
            TEXT_HEADER,
            instrument_id=uuid4(),
            target_cik="320193",
            source_snapshot_id="sec-raw-1",
        )
        self.assertEqual(observation.sic_code, "3571")
        self.assertEqual(observation.sic_description, "ELECTRONIC COMPUTERS")
        self.assertEqual(observation.accepted_at, datetime(2025, 2, 1, 21, 15, 30, tzinfo=UTC))
        self.assertEqual(observation.available_at, datetime(2025, 2, 1, 21, 16, 30, tzinfo=UTC))

    def test_parse_selects_subject_company_not_filed_by(self):
        observation = parse_filing_sic(
            TEXT_HEADER_WITH_OTHER_ENTITY,
            instrument_id=uuid4(),
            target_cik="1958140",
            source_snapshot_id="sec-raw-2",
        )
        self.assertEqual(observation.sic_code, "7900")
        with self.assertRaises(SecFilingHeaderError):
            parse_filing_sic(
                TEXT_HEADER_WITH_OTHER_ENTITY,
                instrument_id=uuid4(),
                target_cik="937797",
                source_snapshot_id="sec-raw-2",
            )

    def test_parse_legacy_sgml_header(self):
        observation = parse_filing_sic(
            LEGACY_HEADER,
            instrument_id=uuid4(),
            target_cik="11",
            source_snapshot_id="legacy",
        )
        self.assertEqual(observation.cik, "0000000011")
        self.assertEqual(observation.sic_code, "1311")

    def test_ff12_mapping_has_frozen_expected_boundaries(self):
        expected = {
            "2086": "01_NODUR",
            "3711": "02_DURBL",
            "3531": "03_MANUF",
            "1311": "04_ENRGY",
            "2860": "05_CHEMS",
            "3571": "06_BUSEQ",
            "4813": "07_TELCM",
            "4911": "08_UTILS",
            "5411": "09_SHOPS",
            "2834": "10_HLTH",
            "6021": "11_MONEY",
            "9995": "12_OTHER",
        }
        for sic, sector in expected.items():
            with self.subTest(sic=sic):
                self.assertEqual(map_sic_to_ff12(sic)[0], sector)
        with self.assertRaises(SecFilingHeaderError):
            map_sic_to_ff12("0000")

    def test_sector_history_changes_only_when_ff12_sector_changes(self):
        instrument_id = uuid4()
        first = parse_filing_sic(
            TEXT_HEADER,
            instrument_id=instrument_id,
            target_cik="320193",
            source_snapshot_id="snap-1",
        )
        same_sector_text = TEXT_HEADER.replace(
            "0000320193-25-000001", "0000320193-25-000002"
        ).replace("20250201161530", "20250501162000").replace("[3571]", "[7372]")
        same_sector = parse_filing_sic(
            same_sector_text,
            instrument_id=instrument_id,
            target_cik="320193",
            source_snapshot_id="snap-2",
        )
        changed_text = TEXT_HEADER.replace(
            "0000320193-25-000001", "0000320193-25-000003"
        ).replace("20250201161530", "20250801162000").replace(
            "ELECTRONIC COMPUTERS [3571]", "RETAIL-COMPUTER STORES [5734]"
        )
        changed = parse_filing_sic(
            changed_text,
            instrument_id=instrument_id,
            target_cik="320193",
            source_snapshot_id="snap-3",
        )
        history = build_sector_history([changed, same_sector, first])
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].sector_code, "06_BUSEQ")
        self.assertEqual(history[1].sector_code, "09_SHOPS")
        self.assertEqual(history[0].effective_to, history[1].effective_from)

    def test_future_sector_change_is_not_visible(self):
        instrument_id = uuid4()
        first = parse_filing_sic(
            TEXT_HEADER,
            instrument_id=instrument_id,
            target_cik="320193",
            source_snapshot_id="snap-1",
        )
        changed_text = TEXT_HEADER.replace(
            "0000320193-25-000001", "0000320193-25-000003"
        ).replace("20250201161530", "20250801162000").replace(
            "ELECTRONIC COMPUTERS [3571]", "RETAIL-COMPUTER STORES [5734]"
        )
        changed = parse_filing_sic(
            changed_text,
            instrument_id=instrument_id,
            target_cik="320193",
            source_snapshot_id="snap-3",
        )
        history = build_sector_history([first, changed])
        before = select_sector_as_of(history, decision_at=datetime(2025, 6, 1, tzinfo=UTC))
        after = select_sector_as_of(history, decision_at=datetime(2025, 9, 1, tzinfo=UTC))
        self.assertEqual(before.sector_code, "06_BUSEQ")
        self.assertEqual(after.sector_code, "09_SHOPS")
        with self.assertRaises(PointInTimeError):
            select_sector_as_of(
                history,
                decision_at=first.available_at - timedelta(seconds=1),
            )

    def test_conflicting_same_accession_fails_closed(self):
        instrument_id = uuid4()
        first = parse_filing_sic(
            TEXT_HEADER,
            instrument_id=instrument_id,
            target_cik="320193",
            source_snapshot_id="snap-1",
        )
        conflict = type(first)(
            instrument_id=first.instrument_id,
            cik=first.cik,
            accession_number=first.accession_number,
            form_type=first.form_type,
            sic_code="5734",
            sic_description="Retail",
            accepted_at=first.accepted_at,
            available_at=first.available_at,
            source_snapshot_id="snap-conflict",
            revision=first.revision,
        )
        with self.assertRaises(SecFilingHeaderError):
            build_sector_history([first, conflict])


if __name__ == "__main__":
    unittest.main()

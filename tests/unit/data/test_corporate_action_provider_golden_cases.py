import json
from pathlib import Path


def test_golden_cases_cover_required_economic_shapes():
    path = Path(__file__).parents[2] / "fixtures" / "data" / "corporate_action_provider_golden_cases.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert len(cases) >= 6
    types = {case["action_type"] for case in cases}
    assert {"SPLIT", "REVERSE_SPLIT", "SPINOFF", "ACQUISITION", "MERGER", "BANKRUPTCY"} <= types
    assert all(str(case["official_source"]).startswith("https://") for case in cases)

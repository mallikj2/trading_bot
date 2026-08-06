from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen


class SecEdgarClient:
    """Read-only SEC client with declared user agent and conservative pacing."""

    base_url = "https://data.sec.gov"

    def __init__(self, user_agent: str | None = None, delay_seconds: float = 0.25) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT")
        if not self.user_agent or "@" not in self.user_agent:
            raise ValueError("SEC_USER_AGENT must identify the project and a contact email")
        if delay_seconds < 0.1:
            raise ValueError("delay_seconds is too aggressive")
        self.delay_seconds = delay_seconds

    def _get(self, path: str) -> dict:
        request = Request(
            f"{self.base_url}{path}",
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=60) as response:  # nosec: B310 - fixed HTTPS host
            payload = json.load(response)
        time.sleep(self.delay_seconds)
        return payload

    def submissions(self, cik: str) -> dict:
        return self._get(f"/submissions/CIK{int(cik):010d}.json")

    def companyfacts(self, cik: str) -> dict:
        return self._get(f"/api/xbrl/companyfacts/CIK{int(cik):010d}.json")

    @staticmethod
    def save_raw(payload: dict, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError(f"raw snapshot already exists: {output}")
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

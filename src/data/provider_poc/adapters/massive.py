from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MassiveClient:
    """Minimal read-only client used only by the Phase 02 credentialed trial."""

    base_url = "https://api.massive.com"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("MASSIVE_API_KEY")
        if not self.api_key:
            raise ValueError("MASSIVE_API_KEY is required")

    def get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = dict(params)
        query["apiKey"] = self.api_key
        url = f"{self.base_url}{path}?{urlencode(query)}"
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=60) as response:  # nosec: B310 - fixed HTTPS host
            return json.load(response)

    @staticmethod
    def save_raw(payload: dict[str, Any], output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError(f"raw snapshot already exists: {output}")
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

"""Thin HTTP client for the Naver Commerce API with retry/backoff and a call log."""
from __future__ import annotations

import time
from typing import Any, Callable

from smartstore.auth import TokenProvider
from smartstore.config import Settings

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3

# In-memory call log for observability (same pattern as agent/tools.py CALL_LOG)
CALL_LOG: list[dict[str, Any]] = []


class CommerceAPIError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


class CommerceClient:
    def __init__(self, settings: Settings, session=None, sleep: Callable[[float], None] = time.sleep):
        if session is None:
            import requests

            session = requests.Session()
        self.settings = settings
        self.session = session
        self.sleep = sleep
        self.base_url = settings.base_url.rstrip("/")
        self.tokens = TokenProvider(settings.client_id, settings.client_secret, self.base_url, session)

    def request(self, method: str, path: str, params: dict | None = None, json: Any = None) -> dict:
        attempt = 0
        while True:
            start = time.perf_counter()
            resp = self.session.request(
                method,
                self.base_url + path,
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {self.tokens.get()}"},
                timeout=20,
            )
            CALL_LOG.append({
                "method": method,
                "path": path,
                "status": resp.status_code,
                "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
                "attempt": attempt,
            })
            if resp.status_code == 401 and attempt == 0:
                self.tokens.invalidate()
            elif resp.status_code not in RETRY_STATUSES:
                break
            if attempt >= MAX_RETRIES:
                break
            self.sleep(2 ** attempt)
            attempt += 1

        if resp.status_code >= 400:
            raise CommerceAPIError(resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    def get(self, path: str, **params) -> dict:
        return self.request("GET", path, params=params or None)

    def post(self, path: str, body: Any) -> dict:
        return self.request("POST", path, json=body)

    def put(self, path: str, body: Any) -> dict:
        return self.request("PUT", path, json=body)

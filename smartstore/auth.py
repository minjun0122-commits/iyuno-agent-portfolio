"""Naver Commerce API OAuth2 token (client_credentials, type=SELF).

The signature is bcrypt("{client_id}_{timestamp_ms}", salt=client_secret), then
base64-encoded. The client secret issued by the Commerce API Center is itself a
bcrypt salt ("$2a$04$..."), so the signature is deterministic for a given
timestamp.
"""
from __future__ import annotations

import base64
import time
from typing import Callable

import bcrypt

TOKEN_PATH = "/external/v1/oauth2/token"
REFRESH_MARGIN_S = 60


def make_signature(client_id: str, client_secret: str, timestamp_ms: int) -> str:
    password = f"{client_id}_{timestamp_ms}".encode("utf-8")
    hashed = bcrypt.hashpw(password, client_secret.encode("utf-8"))
    return base64.standard_b64encode(hashed).decode("utf-8")


class TokenProvider:
    """Fetches and caches an access token until shortly before it expires."""

    def __init__(self, client_id: str, client_secret: str, base_url: str, session,
                 clock: Callable[[], float] = time.time):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.clock = clock
        self._token: str | None = None
        self._expires_at = 0.0

    def get(self) -> str:
        now = self.clock()
        if self._token and now < self._expires_at - REFRESH_MARGIN_S:
            return self._token
        ts = int(now * 1000)
        resp = self.session.post(
            self.base_url + TOKEN_PATH,
            data={
                "client_id": self.client_id,
                "timestamp": ts,
                "client_secret_sign": make_signature(self.client_id, self.client_secret, ts),
                "grant_type": "client_credentials",
                "type": "SELF",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"token request failed: HTTP {resp.status_code} {resp.text[:200]}")
        body = resp.json()
        self._token = body["access_token"]
        self._expires_at = now + int(body.get("expires_in", 10800))
        return self._token

    def invalidate(self) -> None:
        self._token = None

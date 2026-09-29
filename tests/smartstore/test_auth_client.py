import base64

import bcrypt

from smartstore.auth import TokenProvider, make_signature
from smartstore.client import CommerceAPIError, CommerceClient
from smartstore.config import Settings

SECRET = "$2a$04$abcdefghijklmnopqrstuu"


def test_signature_is_deterministic_bcrypt():
    a = make_signature("my-client", SECRET, 1700000000000)
    b = make_signature("my-client", SECRET, 1700000000000)
    assert a == b
    hashed = base64.standard_b64decode(a)
    assert hashed.startswith(b"$2a$04$")
    assert bcrypt.checkpw(b"my-client_1700000000000", hashed)
    assert make_signature("my-client", SECRET, 1700000000001) != a


class FakeResp:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body or {}
        self.text = str(self._body)
        self.content = b"x"

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.token_calls = 0
        self.calls = []

    def post(self, url, data=None, timeout=None):
        self.token_calls += 1
        return FakeResp(200, {"access_token": f"tok{self.token_calls}", "expires_in": 10800})

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw["headers"]["Authorization"]))
        return self.responses.pop(0)


def _client(responses):
    session = FakeSession(responses)
    client = CommerceClient(Settings(client_id="id", client_secret=SECRET), session=session, sleep=lambda s: None)
    return client, session


def test_token_cached_between_calls():
    session = FakeSession([])
    clock = [1000.0]
    tp = TokenProvider("id", SECRET, "https://x", session, clock=lambda: clock[0])
    assert tp.get() == "tok1"
    clock[0] += 3600
    assert tp.get() == "tok1"
    clock[0] += 10800
    assert tp.get() == "tok2"


def test_client_retries_on_429_then_succeeds():
    client, session = _client([FakeResp(429), FakeResp(503), FakeResp(200, {"data": 1})])
    assert client.get("/p") == {"data": 1}
    assert len(session.calls) == 3


def test_client_refreshes_token_on_401():
    client, session = _client([FakeResp(401), FakeResp(200, {"ok": True})])
    assert client.get("/p") == {"ok": True}
    assert session.calls[0][2] == "Bearer tok1"
    assert session.calls[1][2] == "Bearer tok2"


def test_client_raises_on_4xx():
    client, _ = _client([FakeResp(400, {"message": "bad"})])
    try:
        client.post("/p", {})
    except CommerceAPIError as e:
        assert e.status == 400
    else:
        raise AssertionError("expected CommerceAPIError")

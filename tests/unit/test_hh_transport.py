from urllib.parse import parse_qs, urlparse

import pytest

from core.exceptions import ClientError
from infrastructure.hh import AiohttpHHClient


class Response:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def json(self):
        return self.payload


class Session:
    responses: list[Response] = []
    calls: list[tuple[str, str, object, object]] = []

    def __init__(self, **kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def request(self, method, url, *, data=None, headers=None):
        self.calls.append((method, url, data, headers))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_hh_transport_contract_and_single_redirect(monkeypatch) -> None:
    monkeypatch.setattr("infrastructure.hh.aiohttp.ClientSession", Session)
    Session.calls = []
    Session.responses = [
        Response(200, {"access_token": "a", "refresh_token": "r", "expires_in": 60}),
        Response(200, {"id": "hh-1"}),
    ]
    client = AiohttpHHClient(
        client_id="client",
        client_secret="secret",
        redirect_url="http://localhost:3101/auth/hh/",
        auth_url="https://hh/auth",
        token_url="https://hh/token",
        profile_url="https://hh/me",
    )
    query = parse_qs(urlparse(client.authorization_url(state="opaque")).query)
    assert query == {
        "response_type": ["code"],
        "client_id": ["client"],
        "redirect_uri": ["http://localhost:3101/auth/hh/"],
        "state": ["opaque"],
    }
    tokens = await client.exchange_code(code="one-time")
    profile = await client.get_profile(access_token=tokens.access_token)
    assert profile == {"id": "hh-1"}
    token_data = Session.calls[0][2]
    assert isinstance(token_data, dict)
    assert token_data["redirect_uri"] == "http://localhost:3101/auth/hh/"
    assert Session.calls[1][3] == {"Authorization": "Bearer a"}


@pytest.mark.asyncio
async def test_hh_transport_maps_remote_and_invalid_payload_errors(monkeypatch) -> None:
    monkeypatch.setattr("infrastructure.hh.aiohttp.ClientSession", Session)
    client = AiohttpHHClient(
        client_id="c",
        client_secret="s",
        redirect_url="https://app/callback",
        auth_url="https://hh/auth",
        token_url="https://hh/token",
        profile_url="https://hh/me",
    )
    Session.responses = [Response(503, {"error": "secret details"})]
    with pytest.raises(ClientError, match="Операция HH"):
        await client.exchange_code(code="code")
    Session.responses = [Response(200, [])]
    with pytest.raises(ClientError, match="некорректный"):
        await client.get_profile(access_token="token")

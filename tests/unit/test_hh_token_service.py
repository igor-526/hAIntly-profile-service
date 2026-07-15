from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from core.entities import HHAccount, HHTokens
from core.exceptions import ClientError, HHRefreshError
from core.services import HHAccountService
from infrastructure.crypto import TokenCrypto


class FakeHHWithRefresh:
    def __init__(self, *, tokens: HHTokens | None = None, error: Exception | None = None) -> None:
        self._tokens = tokens
        self._error = error
        self.refresh_calls: list[str] = []

    def authorization_url(self, *, state: str) -> str:
        return f"https://hh.test/auth?state={state}"

    async def exchange_code(self, *, code: str) -> HHTokens:
        return HHTokens(
            access_token="access", refresh_token="refresh", expires_at=datetime.now(UTC) + timedelta(hours=1)
        )

    async def get_profile(self, *, access_token: str) -> dict[str, object]:
        return {"id": "hh-1", "first_name": "Иван", "last_name": "Иванов", "email": "i@example.test"}

    async def refresh_token(self, *, refresh_token: str) -> HHTokens:
        self.refresh_calls.append(refresh_token)
        if self._error:
            raise self._error
        return self._tokens  # type: ignore[return-value]


class MemoryAccounts:
    def __init__(self) -> None:
        self.items: dict[object, HHAccount] = {}

    async def get_by_hh_user_id(self, *, hh_user_id):
        return next((item for item in self.items.values() if item.hh_user_id == hh_user_id), None)

    async def get(self, *, user_id, account_id):
        item = self.items.get(account_id)
        return item if item and item.user_id == user_id else None

    async def list(self, *, user_id):
        return [item for item in self.items.values() if item.user_id == user_id]

    async def save(self, *, account):
        self.items[account.id] = account
        return account

    async def delete(self, *, user_id, account_id):
        if await self.get(user_id=user_id, account_id=account_id):
            del self.items[account_id]
            return True
        return False


def _make_account(
    *,
    user_id=None,
    access_token="access",
    refresh_token="refresh",
    expires_at=None,
    crypto=None,
) -> tuple[HHAccount, TokenCrypto]:
    if crypto is None:
        crypto = TokenCrypto(Fernet.generate_key().decode())
    account = HHAccount(
        user_id=user_id or uuid4(),
        hh_user_id="hh-1",
        profile={"id": "hh-1", "first_name": "Иван", "email": "i@example.test"},
        access_token_ciphertext=crypto.encrypt(access_token),
        refresh_token_ciphertext=crypto.encrypt(refresh_token),
        access_token_expires_at=expires_at or (datetime.now(UTC) + timedelta(hours=1)),
    )
    return account, crypto


@pytest.mark.asyncio
async def test_get_access_token_without_refresh() -> None:
    crypto = TokenCrypto(Fernet.generate_key().decode())
    account, crypto = _make_account(crypto=crypto)
    repo = MemoryAccounts()
    repo.items[account.id] = account
    hh = FakeHHWithRefresh()
    service = HHAccountService(accounts=repo, hh=hh, crypto=crypto)

    result = await service.get_access_token(account_id=account.id, user_id=account.user_id, refresh=False)

    assert result is not None
    token, expires_at = result
    assert token == "access"
    assert expires_at == account.access_token_expires_at
    assert hh.refresh_calls == []


@pytest.mark.asyncio
async def test_get_access_token_with_refresh_token_fresh() -> None:
    crypto = TokenCrypto(Fernet.generate_key().decode())
    account, crypto = _make_account(
        crypto=crypto,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    repo = MemoryAccounts()
    repo.items[account.id] = account
    new_tokens = HHTokens(
        access_token="new_access", refresh_token="new_refresh", expires_at=datetime.now(UTC) + timedelta(hours=2)
    )
    hh = FakeHHWithRefresh(tokens=new_tokens)
    service = HHAccountService(accounts=repo, hh=hh, crypto=crypto)

    result = await service.get_access_token(account_id=account.id, user_id=account.user_id, refresh=True)

    assert result is not None
    token, _ = result
    assert token == "access"
    assert hh.refresh_calls == []


@pytest.mark.asyncio
async def test_get_access_token_with_refresh_token_expiring() -> None:
    crypto = TokenCrypto(Fernet.generate_key().decode())
    account, crypto = _make_account(
        crypto=crypto,
        access_token="old_access",
        refresh_token="old_refresh",
        expires_at=datetime.now(UTC) + timedelta(seconds=30),
    )
    repo = MemoryAccounts()
    repo.items[account.id] = account
    new_tokens = HHTokens(
        access_token="new_access", refresh_token="new_refresh", expires_at=datetime.now(UTC) + timedelta(hours=2)
    )
    hh = FakeHHWithRefresh(tokens=new_tokens)
    service = HHAccountService(accounts=repo, hh=hh, crypto=crypto)

    result = await service.get_access_token(account_id=account.id, user_id=account.user_id, refresh=True)

    assert result is not None
    token, expires_at = result
    assert token == "new_access"
    assert hh.refresh_calls == ["old_refresh"]
    stored = repo.items[account.id]
    assert crypto.decrypt(stored.access_token_ciphertext) == "new_access"
    assert crypto.decrypt(stored.refresh_token_ciphertext) == "new_refresh"


@pytest.mark.asyncio
async def test_get_access_token_account_not_found() -> None:
    crypto = TokenCrypto(Fernet.generate_key().decode())
    repo = MemoryAccounts()
    hh = FakeHHWithRefresh()
    service = HHAccountService(accounts=repo, hh=hh, crypto=crypto)

    result = await service.get_access_token(account_id=uuid4(), user_id=uuid4(), refresh=False)

    assert result is None


@pytest.mark.asyncio
async def test_get_access_token_refresh_propagates_hh_refresh_error() -> None:
    crypto = TokenCrypto(Fernet.generate_key().decode())
    account, crypto = _make_account(
        crypto=crypto,
        expires_at=datetime.now(UTC) + timedelta(seconds=30),
    )
    repo = MemoryAccounts()
    repo.items[account.id] = account
    hh = FakeHHWithRefresh(error=HHRefreshError("invalid_grant"))
    service = HHAccountService(accounts=repo, hh=hh, crypto=crypto)

    with pytest.raises(HHRefreshError):
        await service.get_access_token(account_id=account.id, user_id=account.user_id, refresh=True)


@pytest.mark.asyncio
async def test_get_access_token_refresh_propagates_client_error() -> None:
    crypto = TokenCrypto(Fernet.generate_key().decode())
    account, crypto = _make_account(
        crypto=crypto,
        expires_at=datetime.now(UTC) + timedelta(seconds=30),
    )
    repo = MemoryAccounts()
    repo.items[account.id] = account
    hh = FakeHHWithRefresh(error=ClientError("network error"))
    service = HHAccountService(accounts=repo, hh=hh, crypto=crypto)

    with pytest.raises(ClientError):
        await service.get_access_token(account_id=account.id, user_id=account.user_id, refresh=True)

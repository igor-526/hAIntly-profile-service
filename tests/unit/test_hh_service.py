from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from core.entities import HHAccount, HHTokens
from core.exceptions import AlreadyExistsError
from core.services import HHAccountService
from infrastructure.crypto import TokenCrypto


class FakeHH:
    def authorization_url(self, *, state: str) -> str:
        return f"https://hh.test/auth?state={state}"

    async def exchange_code(self, *, code: str) -> HHTokens:
        return HHTokens(
            access_token="access", refresh_token="refresh", expires_at=datetime.now(UTC) + timedelta(hours=1)
        )

    async def refresh_token(self, *, refresh_token: str) -> HHTokens:
        return HHTokens(
            access_token="access", refresh_token=refresh_token, expires_at=datetime.now(UTC) + timedelta(hours=1)
        )

    async def get_profile(self, *, access_token: str) -> dict[str, object]:
        return {"id": "hh-1", "first_name": "Иван", "last_name": "Иванов", "email": "i@example.test"}


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


@pytest.mark.asyncio
async def test_complete_relink_owner_scope_and_safe_dto() -> None:
    repository = MemoryAccounts()
    service = HHAccountService(accounts=repository, hh=FakeHH(), crypto=TokenCrypto(Fernet.generate_key().decode()))
    owner = uuid4()
    output = await service.complete(user_id=owner, code="code")
    stored = next(iter(repository.items.values()))
    assert output.display_name == "Иван Иванов"
    assert "token" not in output.model_dump_json()
    assert stored.access_token_ciphertext != "access"
    relinked = await service.complete(user_id=owner, code="new-code")
    assert relinked.id == output.id
    with pytest.raises(AlreadyExistsError):
        await service.complete(user_id=uuid4(), code="code")
    assert await service.get(user_id=uuid4(), account_id=output.id) is None
    assert await service.delete(user_id=owner, account_id=output.id)
    assert not await service.delete(user_id=owner, account_id=output.id)

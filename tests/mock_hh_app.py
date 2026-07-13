from datetime import UTC, datetime
from uuid import UUID, uuid4

from core.schemas import HHAccountOut
from depends.services import get_hh_account_service
from main import app


class MockHHAccountService:
    def __init__(self) -> None:
        self.account = HHAccountOut(id=uuid4(), hh_user_id="mock-hh-user", display_name="Mock HH",
                                    email=None, avatar_url=None, created_at=datetime.now(UTC), updated_at=None)

    def authorization_url(self, *, state: str) -> str:
        return f"https://hh.mock/oauth?state={state}"

    async def complete(self, *, user_id: UUID, code: str) -> HHAccountOut:
        return self.account

    async def list(self, *, user_id: UUID) -> list[HHAccountOut]:
        return [self.account]

    async def get(self, *, user_id: UUID, account_id: UUID) -> HHAccountOut | None:
        return self.account if account_id == self.account.id else None

    async def delete(self, *, user_id: UUID, account_id: UUID) -> bool:
        return account_id == self.account.id


service = MockHHAccountService()
app.dependency_overrides[get_hh_account_service] = lambda: service

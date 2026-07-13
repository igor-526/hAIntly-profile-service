from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from core.entities import HHAccount
from models import hh_accounts


class HHAccountRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _entity(row: RowMapping) -> HHAccount:
        return HHAccount.model_validate(dict(row))

    async def get_by_hh_user_id(self, *, hh_user_id: str) -> HHAccount | None:
        result = await self.session.execute(select(hh_accounts).where(hh_accounts.c.hh_user_id == hh_user_id))
        row = result.mappings().first()
        return self._entity(row) if row else None

    async def get(self, *, user_id: UUID, account_id: UUID) -> HHAccount | None:
        row = (
            (
                await self.session.execute(
                    select(hh_accounts).where(hh_accounts.c.id == account_id, hh_accounts.c.user_id == user_id)
                )
            )
            .mappings()
            .first()
        )
        return self._entity(row) if row else None

    async def list(self, *, user_id: UUID) -> list[HHAccount]:
        rows = (
            (
                await self.session.execute(
                    select(hh_accounts)
                    .where(hh_accounts.c.user_id == user_id)
                    .order_by(hh_accounts.c.created_at, hh_accounts.c.id)
                )
            )
            .mappings()
            .all()
        )
        return [self._entity(row) for row in rows]

    async def save(self, *, account: HHAccount) -> HHAccount:
        values = account.model_dump(exclude={"updated_at"})
        existing = await self.get_by_hh_user_id(hh_user_id=account.hh_user_id)
        statement = (
            update(hh_accounts)
            .where(hh_accounts.c.id == existing.id)
            .values(**{k: v for k, v in values.items() if k not in {"id", "created_at"}})
            .returning(hh_accounts)
            if existing
            else insert(hh_accounts).values(**values).returning(hh_accounts)
        )
        row = (await self.session.execute(statement)).mappings().one()
        return self._entity(row)

    async def delete(self, *, user_id: UUID, account_id: UUID) -> bool:
        result = await self.session.execute(
            delete(hh_accounts).where(hh_accounts.c.id == account_id, hh_accounts.c.user_id == user_id)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

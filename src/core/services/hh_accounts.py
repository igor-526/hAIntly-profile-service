from uuid import UUID

from core.entities import HHAccount
from core.exceptions import AlreadyExistsError, ClientError
from core.protocols import HHAccountRepositoryProtocol, HHClientProtocol
from core.schemas import HHAccountOut
from infrastructure.crypto import TokenCrypto


class HHAccountService:
    def __init__(self, *, accounts: HHAccountRepositoryProtocol, hh: HHClientProtocol, crypto: TokenCrypto) -> None:
        self.accounts = accounts
        self.hh = hh
        self.crypto = crypto

    def authorization_url(self, *, state: str) -> str:
        return self.hh.authorization_url(state=state)

    async def complete(self, *, user_id: UUID, code: str) -> HHAccountOut:
        tokens = await self.hh.exchange_code(code=code)
        profile = await self.hh.get_profile(access_token=tokens.access_token)
        hh_user_id = str(profile.get("id", "")).strip()
        if not hh_user_id:
            raise ClientError("HH не вернул идентификатор пользователя")
        existing = await self.accounts.get_by_hh_user_id(hh_user_id=hh_user_id)
        if existing is not None and existing.user_id != user_id:
            raise AlreadyExistsError("Этот HH-аккаунт уже связан")
        access_ciphertext = self.crypto.encrypt(tokens.access_token)
        refresh_ciphertext = self.crypto.encrypt(tokens.refresh_token)
        if existing:
            account = HHAccount(
                id=existing.id,
                created_at=existing.created_at,
                user_id=user_id,
                hh_user_id=hh_user_id,
                profile=profile,
                access_token_ciphertext=access_ciphertext,
                refresh_token_ciphertext=refresh_ciphertext,
                access_token_expires_at=tokens.expires_at,
            )
        else:
            account = HHAccount(
                user_id=user_id,
                hh_user_id=hh_user_id,
                profile=profile,
                access_token_ciphertext=access_ciphertext,
                refresh_token_ciphertext=refresh_ciphertext,
                access_token_expires_at=tokens.expires_at,
            )
        return self._out(await self.accounts.save(account=account))

    async def list(self, *, user_id: UUID) -> list[HHAccountOut]:
        return [self._out(account) for account in await self.accounts.list(user_id=user_id)]

    async def get(self, *, user_id: UUID, account_id: UUID) -> HHAccountOut | None:
        account = await self.accounts.get(user_id=user_id, account_id=account_id)
        return self._out(account) if account else None

    async def delete(self, *, user_id: UUID, account_id: UUID) -> bool:
        return await self.accounts.delete(user_id=user_id, account_id=account_id)

    @staticmethod
    def _out(account: HHAccount) -> HHAccountOut:
        profile = account.profile
        first = str(profile.get("first_name") or "").strip()
        last = str(profile.get("last_name") or "").strip()
        photo = profile.get("photo")
        avatar = photo.get("small") if isinstance(photo, dict) else None
        return HHAccountOut(
            id=account.id,
            hh_user_id=account.hh_user_id,
            display_name=" ".join(part for part in (first, last) if part) or None,
            email=str(profile["email"]) if profile.get("email") else None,
            avatar_url=str(avatar) if avatar else None,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

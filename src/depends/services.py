from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import HHAccountService
from infrastructure import AiohttpHHClient, TokenCrypto
from repositories import HHAccountRepository
from settings import settings
from utils.database import get_session


async def get_hh_account_service(session: Annotated[AsyncSession, Depends(get_session)]) -> HHAccountService:
    return HHAccountService(
        accounts=HHAccountRepository(session=session),
        hh=AiohttpHHClient(
            client_id=settings.hh_client_id,
            client_secret=settings.hh_client_secret,
            redirect_url=str(settings.hh_redirect_url),
            auth_url=str(settings.hh_auth_url),
            token_url=str(settings.hh_token_url),
            profile_url=str(settings.hh_profile_url),
        ),
        crypto=TokenCrypto(settings.hh_token_encrypt_key),
    )

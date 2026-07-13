from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .base import Entity, TimestampMixin


class HHAccount(Entity, TimestampMixin):
    user_id: UUID
    hh_user_id: str
    profile: dict[str, object]
    access_token_ciphertext: str
    refresh_token_ciphertext: str
    access_token_expires_at: datetime


class HHTokens(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime

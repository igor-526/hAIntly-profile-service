from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from .base import Schema


class AuthorizationRequest(Schema):
    model_config = ConfigDict(extra="forbid")
    state: str = Field(min_length=1, max_length=4096)


class AuthorizationResponse(Schema):
    authorization_url: str


class CompleteOAuthRequest(Schema):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=4096)


class HHAccountOut(Schema):
    id: UUID
    hh_user_id: str
    display_name: str | None
    email: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime | None


class HHAccountList(Schema):
    accounts: list[HHAccountOut]

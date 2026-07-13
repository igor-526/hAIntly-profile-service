from sqlalchemy import Column, DateTime, String, Table, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from utils.basemodel import metadata

hh_accounts = Table(
    "hh_accounts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
    Column("hh_user_id", String(255), nullable=False),
    Column("profile", JSONB, nullable=False),
    Column("access_token_ciphertext", String, nullable=False),
    Column("refresh_token_ciphertext", String, nullable=False),
    Column("access_token_expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=True, onupdate=func.now()),
    UniqueConstraint("hh_user_id", name="uq_hh_accounts_hh_user_id"),
)

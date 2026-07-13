from pathlib import Path

from models import hh_accounts


def test_hh_account_model_and_migration_constraints() -> None:
    assert not hh_accounts.c.user_id.nullable
    assert not hh_accounts.c.hh_user_id.nullable
    assert not hh_accounts.c.access_token_ciphertext.nullable
    assert any(constraint.name == "uq_hh_accounts_hh_user_id" for constraint in hh_accounts.constraints)
    migration = Path("src/migration/versions/20260712_0002_hh_accounts.py").read_text()
    assert 'down_revision = "20260710_0001"' in migration
    assert 'op.drop_table("hh_accounts")' in migration

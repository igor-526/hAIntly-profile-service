from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from core.schemas import HHAccountOut
from depends.services import get_hh_account_service
from main import app


def output(account_id=None):
    return HHAccountOut(
        id=account_id or uuid4(),
        hh_user_id="hh-1",
        display_name="Иван",
        email=None,
        avatar_url=None,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


def test_internal_typed_owner_scoped_list_get_delete_contract() -> None:
    owner, account_id = uuid4(), uuid4()
    service = AsyncMock()
    service.list.return_value = [output(account_id)]
    service.get.return_value = output(account_id)
    service.delete.return_value = True
    app.dependency_overrides[get_hh_account_service] = lambda: service
    client = TestClient(app)
    headers = {"X-User-Id": str(owner)}
    try:
        listed = client.post("/internal/hh/accounts/list", headers=headers)
        fetched = client.post(f"/internal/hh/accounts/{account_id}", headers=headers)
        deleted = client.delete(f"/internal/hh/accounts/{account_id}", headers=headers)
    finally:
        app.dependency_overrides.clear()
    assert listed.status_code == fetched.status_code == 200
    assert deleted.status_code == 204
    assert "token" not in listed.text.lower()
    service.list.assert_awaited_once_with(user_id=owner)
    service.get.assert_awaited_once_with(user_id=owner, account_id=account_id)
    service.delete.assert_awaited_once_with(user_id=owner, account_id=account_id)


def test_internal_get_hides_foreign_or_missing_account() -> None:
    service = AsyncMock()
    service.get.return_value = None
    app.dependency_overrides[get_hh_account_service] = lambda: service
    try:
        response = TestClient(app).post(
            f"/internal/hh/accounts/{uuid4()}", headers={"X-User-Id": str(uuid4())}
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json() == {"detail": "HH-аккаунт не найден"}


def test_mock_hh_oauth_api_smoke_without_credentials() -> None:
    account = output()
    service = Mock()
    service.authorization_url.return_value = "https://hh.test/oauth?state=opaque"
    service.complete = AsyncMock()
    service.complete.return_value = account
    app.dependency_overrides[get_hh_account_service] = lambda: service
    client = TestClient(app)
    try:
        started = client.post("/internal/hh/oauth/authorization", json={"state": "opaque"})
        completed = client.post(
            "/internal/hh/oauth/complete", json={"code": "mock-code"}, headers={"X-User-Id": str(uuid4())}
        )
    finally:
        app.dependency_overrides.clear()
    assert started.status_code == completed.status_code == 200
    assert started.json()["authorization_url"].startswith("https://hh.test/")
    assert "mock-code" not in completed.text


def test_user_scoped_endpoints_require_valid_user_header_without_calling_service() -> None:
    service = AsyncMock()
    app.dependency_overrides[get_hh_account_service] = lambda: service
    account_id = uuid4()
    requests = [
        ("POST", "/internal/hh/oauth/complete", {"code": "mock-code"}),
        ("POST", "/internal/hh/accounts/list", None),
        ("POST", f"/internal/hh/accounts/{account_id}", None),
        ("DELETE", f"/internal/hh/accounts/{account_id}", None),
    ]
    try:
        client = TestClient(app)
        for method, path, body in requests:
            for headers in ({}, {"X-User-Id": "invalid"}):
                response = client.request(method, path, json=body, headers=headers)
                assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

    service.complete.assert_not_awaited()
    service.list.assert_not_awaited()
    service.get.assert_not_awaited()
    service.delete.assert_not_awaited()

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from core.exceptions import ClientError, HHRefreshError
from core.schemas import (
    AuthorizationRequest,
    AuthorizationResponse,
    CompleteOAuthRequest,
    HHAccessTokenOut,
    HHAccountList,
    HHAccountOut,
)
from core.services import HHAccountService
from depends.services import get_hh_account_service

router = APIRouter(prefix="/internal/hh", tags=["HH accounts"])


@router.post("/oauth/authorization", response_model=AuthorizationResponse)
async def authorization(
    data: AuthorizationRequest, service: Annotated[HHAccountService, Depends(get_hh_account_service)]
) -> AuthorizationResponse:
    return AuthorizationResponse(authorization_url=service.authorization_url(state=data.state))


@router.post("/oauth/complete", response_model=HHAccountOut)
async def complete(
    data: CompleteOAuthRequest,
    user_id: Annotated[UUID, Header(alias="X-User-Id")],
    service: Annotated[HHAccountService, Depends(get_hh_account_service)],
) -> HHAccountOut:
    return await service.complete(user_id=user_id, code=data.code)


@router.post("/accounts/list", response_model=HHAccountList)
async def list_accounts(
    user_id: Annotated[UUID, Header(alias="X-User-Id")],
    service: Annotated[HHAccountService, Depends(get_hh_account_service)],
) -> HHAccountList:
    return HHAccountList(accounts=await service.list(user_id=user_id))


@router.post("/accounts/{account_id}", response_model=HHAccountOut)
async def get_account(
    account_id: UUID,
    user_id: Annotated[UUID, Header(alias="X-User-Id")],
    service: Annotated[HHAccountService, Depends(get_hh_account_service)],
) -> HHAccountOut:
    account = await service.get(user_id=user_id, account_id=account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="HH-аккаунт не найден")
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    user_id: Annotated[UUID, Header(alias="X-User-Id")],
    service: Annotated[HHAccountService, Depends(get_hh_account_service)],
) -> Response:
    await service.delete(user_id=user_id, account_id=account_id)
    return Response(status_code=204)


@router.get("/hh-token/{account_id}", response_model=HHAccessTokenOut)
async def get_hh_token(
    account_id: UUID,
    user_id: Annotated[UUID, Header(alias="X-User-Id")],
    service: Annotated[HHAccountService, Depends(get_hh_account_service)],
    refresh: bool = Query(default=False),
) -> HHAccessTokenOut:
    try:
        result = await service.get_access_token(account_id=account_id, user_id=user_id, refresh=refresh)
    except HHRefreshError as exc:
        raise HTTPException(
            status_code=401, detail={"detail": "hh_token_refresh_failed", "account_id": str(account_id)}
        ) from exc
    except ClientError as exc:
        raise HTTPException(status_code=502, detail="hh_refresh_error") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="HH-аккаунт не найден")
    access_token, expires_at = result
    return HHAccessTokenOut(access_token=access_token, expires_at=expires_at)

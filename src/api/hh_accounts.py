from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from core.schemas import (
    AuthorizationRequest,
    AuthorizationResponse,
    CompleteOAuthRequest,
    HHAccountList,
    HHAccountOut,
    UserRequest,
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
    data: CompleteOAuthRequest, service: Annotated[HHAccountService, Depends(get_hh_account_service)]
) -> HHAccountOut:
    return await service.complete(user_id=data.user_id, code=data.code)


@router.post("/accounts/list", response_model=HHAccountList)
async def list_accounts(
    data: UserRequest, service: Annotated[HHAccountService, Depends(get_hh_account_service)]
) -> HHAccountList:
    return HHAccountList(accounts=await service.list(user_id=data.user_id))


@router.post("/accounts/{account_id}", response_model=HHAccountOut)
async def get_account(
    account_id: UUID, data: UserRequest, service: Annotated[HHAccountService, Depends(get_hh_account_service)]
) -> HHAccountOut:
    account = await service.get(user_id=data.user_id, account_id=account_id)
    if account is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="HH-аккаунт не найден")
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID, data: UserRequest, service: Annotated[HHAccountService, Depends(get_hh_account_service)]
) -> Response:
    await service.delete(user_id=data.user_id, account_id=account_id)
    return Response(status_code=204)

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import aiohttp

from core.entities import HHTokens
from core.exceptions import ClientError, HHRefreshError


class AiohttpHHClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_url: str,
        auth_url: str,
        token_url: str,
        profile_url: str,
        timeout_seconds: float = 10,
    ) -> None:
        self.client_id = client_id
        self._client_secret = client_secret
        self.redirect_url = redirect_url
        self.auth_url = auth_url
        self.token_url = token_url
        self.profile_url = profile_url
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    def authorization_url(self, *, state: str) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_url,
                "state": state,
            }
        )
        return f"{self.auth_url}?{query}"

    async def exchange_code(self, *, code: str) -> HHTokens:
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": self.redirect_url,
        }
        data = await self._request("POST", self.token_url, data=payload)
        try:
            return HHTokens(
                access_token=str(data["access_token"]),
                refresh_token=str(data["refresh_token"]),
                expires_at=datetime.now(UTC) + timedelta(seconds=int(str(data["expires_in"]))),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ClientError("HH вернул некорректный ответ") from exc

    async def refresh_token(self, *, refresh_token: str) -> HHTokens:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        try:
            data = await self._request("POST", self.token_url, data=payload)
        except ClientError as exc:
            if "invalid_grant" in str(exc.message).lower():
                raise HHRefreshError("HH refresh token недействителен") from exc
            raise
        try:
            return HHTokens(
                access_token=str(data["access_token"]),
                refresh_token=str(data["refresh_token"]),
                expires_at=datetime.now(UTC) + timedelta(seconds=int(str(data["expires_in"]))),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ClientError("HH вернул некорректный ответ") from exc

    async def get_profile(self, *, access_token: str) -> dict[str, object]:
        return await self._request("GET", self.profile_url, headers={"Authorization": f"Bearer {access_token}"})

    async def _request(
        self, method: str, url: str, *, data: dict[str, str] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, object]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(method, url, data=data, headers=headers) as response:
                    if response.status >= 400:
                        body = await response.text()
                        raise ClientError(f"Операция HH не выполнена: {body}")
                    data = await response.json()
                    if not isinstance(data, dict):
                        raise ClientError("HH вернул некорректный ответ")
                    return {str(key): value for key, value in data.items()}
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ClientError("Сервис HH временно недоступен") from exc

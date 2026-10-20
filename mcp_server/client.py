from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class PolicyApiError(RuntimeError):
    """Base error with an MCP-facing error code."""

    code = "INTERNAL_ERROR"


class InvalidArgumentError(PolicyApiError):
    code = "INVALID_ARGUMENT"


class DocumentNotFoundError(PolicyApiError):
    code = "NOT_FOUND"


class UnauthorizedError(PolicyApiError):
    code = "UNAUTHORIZED"


class ForbiddenError(PolicyApiError):
    code = "FORBIDDEN"


class UpstreamUnavailableError(PolicyApiError):
    code = "UPSTREAM_UNAVAILABLE"


class PolicyApiClient:
    """Small read-only client for the existing FastAPI service."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 15.0,
        default_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_token = default_token
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds),
            headers={"accept": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip()[:500]
        if isinstance(payload, dict):
            detail = payload.get("detail", payload)
        else:
            detail = payload
        return str(detail)[:500]

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        not_found_message: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        bearer = token or self.default_token
        headers = kwargs.pop("headers", {})
        if bearer:
            headers = {**headers, "Authorization": f"Bearer {bearer}"}
        try:
            response = await self._client.request(
                method, path, headers=headers or None, **kwargs
            )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            raise UpstreamUnavailableError(
                "UPSTREAM_UNAVAILABLE: 无法连接 PolicySearcher API，"
                "请确认 FastAPI 已启动且 POLICY_API_URL 正确。"
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(
                f"UPSTREAM_UNAVAILABLE: 调用 PolicySearcher API 失败: {exc}"
            ) from exc

        if response.status_code == 401:
            raise UnauthorizedError(f"UNAUTHORIZED: {self._detail(response)}")
        if response.status_code == 403:
            raise ForbiddenError(f"FORBIDDEN: {self._detail(response)}")
        if response.status_code == 404:
            if not_found_message:
                detail = self._detail(response)
                raise DocumentNotFoundError(
                    f"NOT_FOUND: {detail or not_found_message}"
                )
            raise UpstreamUnavailableError(
                f"UPSTREAM_UNAVAILABLE: API 端点不存在: {path}"
            )
        if 400 <= response.status_code < 500:
            raise InvalidArgumentError(
                f"INVALID_ARGUMENT: {self._detail(response)}"
            )
        if response.status_code >= 500:
            raise UpstreamUnavailableError(
                f"UPSTREAM_UNAVAILABLE: API 返回 HTTP {response.status_code}: "
                f"{self._detail(response)}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise UpstreamUnavailableError(
                "UPSTREAM_UNAVAILABLE: API 返回了非 JSON 响应。"
            ) from exc

    async def search(
        self, payload: dict[str, Any], token: str | None = None
    ) -> dict[str, Any]:
        return await self._request("POST", "/api/search", token=token, json=payload)

    async def get_document(
        self, doc_id: str, token: str | None = None
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/api/documents/{quote(doc_id, safe='')}",
            token=token,
            not_found_message="文档不存在",
        )

    async def stats(self, token: str | None = None) -> dict[str, Any]:
        return await self._request("GET", "/api/stats", token=token)

    async def verify_token(self, token: str) -> dict[str, Any]:
        return await self._request("GET", "/api/auth/verify", token=token)

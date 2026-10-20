from __future__ import annotations

from mcp.server.auth.provider import AccessToken, TokenVerifier

from .client import PolicyApiClient, PolicyApiError


class PolicyTokenVerifier(TokenVerifier):
    """Validate an incoming MCP bearer token against the FastAPI auth service."""

    def __init__(self, client: PolicyApiClient) -> None:
        self._client = client

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = await self._client.verify_token(token)
        except PolicyApiError:
            return None

        subject = str(payload.get("subject") or "policy-client")
        return AccessToken(
            token=token,
            client_id=subject,
            scopes=[str(scope) for scope in payload.get("scopes", [])],
            expires_at=payload.get("expires_at"),
            subject=subject,
            claims={
                "role": payload.get("role"),
                "token_type": payload.get("token_type"),
            },
        )

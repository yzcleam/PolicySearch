from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import ApiToken

settings = get_settings()
security = HTTPBearer(auto_error=False)

API_SCOPE = "policy:read"
ADMIN_SCOPE = "admin"


def _utc_timestamp(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


@dataclass(frozen=True)
class AuthPrincipal:
    subject: str
    role: str
    scopes: list[str] = field(default_factory=list)
    token_type: str = "api"
    jti: str | None = None
    expires_at: int | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _unauthorized(detail: str = "未提供有效的 Bearer Token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str = "权限不足") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def hash_password(password: str, iterations: int = 310_000) -> str:
    """PBKDF2-SHA256 hash used by tests and local tooling."""

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations, dklen=32
    )
    return (
        f"pbkdf2_sha256:{iterations}:"
        f"{base64.urlsafe_b64encode(salt).decode().rstrip('=')}:"
        f"{base64.urlsafe_b64encode(digest).decode().rstrip('=')}"
    )


def verify_password(password: str, encoded: str) -> bool:
    if not encoded:
        return False
    try:
        separator = "$" if "$" in encoded else ":"
        algorithm, iteration_text, salt_text, digest_text = encoded.split(
            separator, 3
        )
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iteration_text)
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(
            digest_text + "=" * (-len(digest_text) % 4)
        )
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def verify_admin_credentials(username: str, password: str) -> bool:
    if not hmac.compare_digest(username, settings.admin_username):
        return False
    return verify_password(password, settings.admin_password_hash)


def _encode(payload: dict) -> str:
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_admin_token() -> tuple[str, int]:
    now = int(time.time())
    expires_in = settings.jwt_expire_minutes * 60
    token = _encode(
        {
            "sub": settings.admin_username,
            "role": "admin",
            "type": "admin",
            "scopes": [ADMIN_SCOPE, API_SCOPE],
            "jti": uuid.uuid4().hex,
            "iat": now,
            "exp": now + expires_in,
        }
    )
    return token, expires_in


def create_api_token_jwt(
    *,
    jti: str,
    name: str,
    scopes: list[str],
    expires_at: datetime | None,
) -> str:
    now = int(time.time())
    payload: dict = {
        "sub": f"token:{name}",
        "role": "api",
        "type": "api",
        "name": name,
        "scopes": scopes,
        "jti": jti,
        "iat": now,
    }
    if expires_at is not None:
        payload["exp"] = _utc_timestamp(expires_at)
    return _encode(payload)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise _unauthorized("Bearer Token 无效或已过期") from exc


def _principal_from_payload(payload: dict) -> AuthPrincipal:
    token_type = str(payload.get("type", "api"))
    role = str(payload.get("role", "api"))
    scopes = [str(scope) for scope in payload.get("scopes", [])]
    return AuthPrincipal(
        subject=str(payload.get("sub", "")),
        role=role,
        scopes=scopes,
        token_type=token_type,
        jti=payload.get("jti"),
        expires_at=int(payload["exp"]) if payload.get("exp") else None,
    )


def _check_api_token_row(
    db: Session, jti: str | None, scopes: list[str]
) -> AuthPrincipal:
    if not jti:
        raise _unauthorized("API Token 缺少 jti")
    row = db.get(ApiToken, jti)
    if row is None:
        raise _unauthorized("API Token 不存在或已被撤销")
    now = datetime.utcnow()
    if row.revoked_at is not None:
        raise _unauthorized("API Token 已被撤销")
    if row.expires_at is not None and row.expires_at <= now:
        raise _unauthorized("API Token 已过期")

    row.last_used_at = now
    db.commit()
    return AuthPrincipal(
        subject=row.name,
        role="api",
        scopes=list(row.scopes or scopes),
        token_type="api",
        jti=row.jti,
        expires_at=_utc_timestamp(row.expires_at) if row.expires_at else None,
    )


async def get_optional_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> AuthPrincipal | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer":
        raise _unauthorized("Authorization 必须使用 Bearer 方案")

    payload = decode_token(credentials.credentials)
    principal = _principal_from_payload(payload)
    if principal.token_type == "admin":
        if not principal.is_admin:
            raise _forbidden("管理员 Token 权限异常")
        return principal
    if principal.token_type != "api":
        raise _unauthorized("不支持的 Token 类型")
    return _check_api_token_row(db, principal.jti, principal.scopes)


async def require_principal(
    principal: AuthPrincipal | None = Depends(get_optional_principal),
) -> AuthPrincipal:
    if principal is None:
        raise _unauthorized()
    return principal


async def require_admin(
    principal: AuthPrincipal | None = Depends(get_optional_principal),
) -> AuthPrincipal:
    if principal is None:
        raise _unauthorized()
    if not principal.is_admin:
        raise _forbidden("需要管理员权限")
    return principal


async def require_api_access(
    principal: AuthPrincipal | None = Depends(get_optional_principal),
) -> AuthPrincipal | None:
    if principal is None:
        if settings.auth_required:
            raise _unauthorized()
        return None
    if not principal.is_admin and API_SCOPE not in principal.scopes:
        raise _forbidden(f"缺少 {API_SCOPE} 权限")
    return principal

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from ..auth import create_api_token_jwt
from ..database import SessionLocal
from ..models import ApiToken

ALLOWED_API_SCOPES = {"policy:read"}


def normalize_scopes(scopes: list[str]) -> list[str]:
    cleaned = sorted({scope.strip() for scope in scopes if scope and scope.strip()})
    if not cleaned:
        cleaned = ["policy:read"]
    unknown = set(cleaned) - ALLOWED_API_SCOPES
    if unknown:
        raise ValueError(f"不支持的 scope: {', '.join(sorted(unknown))}")
    return cleaned


def token_active(row: ApiToken, now: datetime | None = None) -> bool:
    current = now or datetime.utcnow()
    if row.revoked_at is not None:
        return False
    return row.expires_at is None or row.expires_at > current


def create_token(
    name: str, scopes: list[str], expires_in_days: int
) -> tuple[str, ApiToken]:
    normalized = normalize_scopes(scopes)
    now = datetime.utcnow()
    expires_at = now + timedelta(days=expires_in_days)
    jti = uuid.uuid4().hex
    token = create_api_token_jwt(
        jti=jti,
        name=name,
        scopes=normalized,
        expires_at=expires_at,
    )
    row = ApiToken(
        jti=jti,
        name=name,
        scopes=normalized,
        created_at=now,
        expires_at=expires_at,
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
    return token, row


def list_tokens() -> list[ApiToken]:
    with SessionLocal() as session:
        return list(
            session.query(ApiToken)
            .order_by(ApiToken.created_at.desc())
            .all()
        )


def revoke_token(jti: str) -> ApiToken | None:
    with SessionLocal() as session:
        row = session.get(ApiToken, jti)
        if row is None:
            return None
        if row.revoked_at is None:
            row.revoked_at = datetime.utcnow()
            session.commit()
            session.refresh(row)
        return row

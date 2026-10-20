from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import (
    AuthPrincipal,
    create_admin_token,
    require_admin,
    require_principal,
    verify_admin_credentials,
)
from ..schemas import (
    AdminMe,
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenInfo,
    ApiTokenList,
    LoginRequest,
    TokenResponse,
    VerifyTokenResponse,
)
from ..services import token_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
tokens_router = APIRouter(
    prefix="/api/admin/tokens",
    tags=["admin-tokens"],
    dependencies=[Depends(require_admin)],
)


def _token_info(row) -> ApiTokenInfo:
    return ApiTokenInfo(
        jti=row.jti,
        name=row.name,
        scopes=list(row.scopes or []),
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
        active=token_service.token_active(row),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    if not verify_admin_credentials(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_admin_token()
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=AdminMe)
def me(principal: AuthPrincipal = Depends(require_admin)) -> AdminMe:
    return AdminMe(
        username=principal.subject,
        role=principal.role,
        scopes=principal.scopes,
        expires_at=principal.expires_at,
    )


@router.get("/verify", response_model=VerifyTokenResponse)
def verify(principal: AuthPrincipal = Depends(require_principal)) -> VerifyTokenResponse:
    return VerifyTokenResponse(
        subject=principal.subject,
        role=principal.role,
        scopes=principal.scopes,
        token_type=principal.token_type,
        expires_at=principal.expires_at,
        jti=principal.jti,
    )


@tokens_router.get("", response_model=ApiTokenList)
def list_tokens() -> ApiTokenList:
    return ApiTokenList(
        tokens=[_token_info(row) for row in token_service.list_tokens()]
    )


@tokens_router.post("", response_model=ApiTokenCreated)
def create_token(req: ApiTokenCreate) -> ApiTokenCreated:
    try:
        token, row = token_service.create_token(
            name=req.name,
            scopes=req.scopes,
            expires_in_days=req.expires_in_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiTokenCreated(token=token, token_info=_token_info(row))


@tokens_router.delete("/{jti}", response_model=ApiTokenInfo)
def revoke_token(jti: str) -> ApiTokenInfo:
    row = token_service.revoke_token(jti)
    if row is None:
        raise HTTPException(status_code=404, detail="Token 不存在")
    return _token_info(row)

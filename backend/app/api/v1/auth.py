from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update

from app.api.deps import CurrentUser, DBSession
from app.core.audit import AuditAction, AuditContext, log_audit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.user import LoginRequest, PasswordChange, Token, TokenRefresh, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    body: LoginRequest,
    db: DBSession,
) -> Token:
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive account")

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            last_login=datetime.now(timezone.utc),
            last_ip=request.client.host if request.client else "",
        )
    )
    await db.commit()

    await log_audit(
        AuditContext(
            user_id=user.id,
            action=AuditAction.LOGIN,
            resource_type="user",
            resource_id=user.id,
            ip_address=request.client.host if request.client else "",
            request_id=getattr(request.state, "request_id", ""),
        ),
        db=db,
    )

    token_data = {"sub": str(user.id), "scopes": user.scopes}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=Token)
async def refresh(body: TokenRefresh, db: DBSession) -> Token:
    try:
        payload = verify_token(body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.id), "scopes": user.scopes}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: PasswordChange,
    user: CurrentUser,
    db: DBSession,
) -> None:
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect")

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(hashed_password=get_password_hash(body.new_password))
    )
    await db.commit()

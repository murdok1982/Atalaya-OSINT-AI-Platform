from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select, update

from app.api.deps import AdminUser, CurrentUser, DBSession, get_token_blacklist
from app.core.audit import AuditAction, AuditContext, log_audit
from app.core.bruteforce import BruteForceProtector
from app.core.events_bus import EventType, AtalayaEvent, event_bus
from app.core.security import (
    create_token_pair,
    get_password_hash,
    validate_password_strength,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.user import LoginRequest, PasswordChange, Token, TokenRefresh, UserResponse, UserCreate

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    body: LoginRequest,
    db: DBSession,
) -> Token:
    client_ip = request.client.host if request.client else "unknown"

    if BruteForceProtector.is_locked(body.username):
        remaining = BruteForceProtector.get_remaining_attempts(body.username)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked. Remaining attempts: {remaining}",
        )

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        BruteForceProtector.record_failure(body.username, client_ip)
        remaining = BruteForceProtector.get_remaining_attempts(body.username)

        await log_audit(
            AuditContext(
                user_id="unknown",
                action=AuditAction.LOGIN,
                resource_type="user",
                resource_id=body.username,
                ip_address=client_ip,
                request_id=getattr(request.state, "request_id", ""),
                success=False,
                error_message="Invalid credentials",
            ),
            db=db,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials. Remaining attempts: {remaining}",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            last_login=datetime.now(timezone.utc),
            last_ip=client_ip,
        )
    )
    await db.commit()

    BruteForceProtector.record_success(body.username, client_ip)

    token_pair = create_token_pair(
        user_id=user.id,
        scopes=user.scopes,
        classification=getattr(user, "classification", "UNCLASSIFIED"),
    )

    await log_audit(
        AuditContext(
            user_id=user.id,
            action=AuditAction.LOGIN,
            resource_type="user",
            resource_id=user.id,
            ip_address=client_ip,
            request_id=getattr(request.state, "request_id", ""),
            success=True,
            details={"session_id": token_pair.session_id},
        ),
        db=db,
    )

    await event_bus.publish(AtalayaEvent(
        event_type=EventType.USER_LOGIN,
        source="auth-service",
        data={"user_id": user.id, "username": user.username, "ip": client_ip},
        tenant_id=getattr(request.state, "tenant_id", ""),
    ))

    return Token(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=Token)
async def refresh(body: TokenRefresh, db: DBSession) -> Token:
    try:
        payload = verify_token(body.refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    blacklist = await get_token_blacklist()
    if await blacklist.is_blacklisted(payload.jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_pair = create_token_pair(
        user_id=user.id,
        scopes=user.scopes,
        session_id=payload.sid,
    )

    await blacklist.add(payload.jti, payload.exp.timestamp() if payload.exp else 0)

    return Token(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    user: CurrentUser,
    db: DBSession,
) -> None:
    from fastapi import Header

    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
        try:
            payload = verify_token(access_token)
            blacklist = await get_token_blacklist()
            await blacklist.add(payload.jti, payload.exp.timestamp() if payload.exp else 0)
        except ValueError:
            pass

    await log_audit(
        AuditContext(
            user_id=user.id,
            action=AuditAction.LOGOUT,
            resource_type="user",
            resource_id=user.id,
            ip_address=request.client.host if request.client else "",
            request_id=getattr(request.state, "request_id", ""),
        ),
        db=db,
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

    issues = validate_password_strength(body.new_password)
    if issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "issues": issues},
        )

    blacklist = await get_token_blacklist()
    await blacklist.add(user.id, 0)

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(hashed_password=get_password_hash(body.new_password))
    )
    await db.commit()


async def _create_user(db, body: UserCreate, request: Request, *, created_by: str) -> User:
    issues = validate_password_strength(body.password)
    if issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "issues": issues},
        )

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name or "",
        scopes=body.scopes or ["read:cases", "write:cases", "execute:jobs"],
        classification=getattr(body, "classification", "UNCLASSIFIED"),
        tenant_id=getattr(body, "tenant_id", "default") or "default",
        department=getattr(body, "department", None),
        phone=getattr(body, "phone", None),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_audit(
        AuditContext(
            user_id=created_by,
            action=AuditAction.CREATE,
            resource_type="user",
            resource_id=user.id,
            ip_address=request.client.host if request.client else "",
            request_id=getattr(request.state, "request_id", ""),
            details={"created_username": user.username, "scopes": user.scopes,
                     "classification": user.classification},
        ),
        db=db,
    )
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    body: UserCreate,
    db: DBSession,
    request: Request,
    admin: AdminUser,
) -> User:
    """Admin-only user provisioning. Self-registration is forbidden in state-grade deployments.

    For the very first user use POST /auth/bootstrap-admin (only succeeds when the users
    table is empty).
    """
    return await _create_user(db, body, request, created_by=admin.id)


@router.post(
    "/bootstrap-admin",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_admin(
    body: UserCreate,
    db: DBSession,
    request: Request,
) -> User:
    """One-shot endpoint: only succeeds when no users exist (fresh install).

    Creates the first superuser. Subsequent calls return 409.
    """
    existing_any = await db.execute(select(User).limit(1))
    if existing_any.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap already complete; use POST /auth/register (admin-only)",
        )

    issues = validate_password_strength(body.password)
    if issues:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "issues": issues},
        )

    admin_scopes = sorted({
        "admin", "read:cases", "write:cases", "read:reports", "write:reports",
        "read:evidence", "write:evidence", "read:entities", "write:entities",
        "read:users", "write:users", "execute:jobs", "audit:log", "system:config",
    })

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name or "Bootstrap Admin",
        is_active=True,
        is_superuser=True,
        scopes=admin_scopes,
        classification=getattr(body, "classification", "TOP_SECRET") or "TOP_SECRET",
        tenant_id=getattr(body, "tenant_id", "default") or "default",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_audit(
        AuditContext(
            user_id=user.id,
            action=AuditAction.CREATE,
            resource_type="user",
            resource_id=user.id,
            ip_address=request.client.host if request.client else "",
            request_id=getattr(request.state, "request_id", ""),
            details={"bootstrap": True, "username": user.username},
        ),
        db=db,
    )
    return user


@router.post("/revoke-all-tokens", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_tokens(
    user: CurrentUser,
    db: DBSession,
) -> None:
    blacklist = await get_token_blacklist()
    await blacklist.revoke_all_user_tokens(user.id, 9999999999.0)
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(last_login=datetime.now(timezone.utc))
    )
    await db.commit()

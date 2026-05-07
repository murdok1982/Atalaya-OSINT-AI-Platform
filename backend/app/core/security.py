from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=14,
)


class Scope(str, Enum):
    READ_CASES = "read:cases"
    WRITE_CASES = "write:cases"
    READ_REPORTS = "read:reports"
    WRITE_REPORTS = "write:reports"
    EXECUTE_JOBS = "execute:jobs"
    ADMIN = "admin"
    TELEGRAM = "telegram"
    READ_EVIDENCE = "read:evidence"
    WRITE_EVIDENCE = "write:evidence"
    READ_ENTITIES = "read:entities"
    WRITE_ENTITIES = "write:entities"
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    AUDIT_LOG = "audit:log"
    SYSTEM_CONFIG = "system:config"


class ClassificationLevel(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    CUI = "CUI"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"
    TOP_SECRET = "TOP_SECRET"


class TokenPayload(BaseModel):
    """Decoded JWT payload. Extra fields (iss/aud) are accepted but ignored."""

    model_config = {"extra": "ignore"}

    sub: str
    scopes: list[str] = []
    type: str = "access"
    exp: datetime | None = None
    jti: str = ""
    iat: datetime | None = None
    sid: str = ""
    classification: str = "UNCLASSIFIED"


class SessionToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    jti: str
    session_id: str


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _generate_jti() -> str:
    return str(uuid.uuid4())


def _generate_session_id() -> str:
    return secrets.token_hex(16)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    session_id: str = "",
    classification: str = "UNCLASSIFIED",
) -> tuple[str, str]:
    to_encode = data.copy()
    jti = _generate_jti()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": jti,
        "iat": datetime.now(timezone.utc),
        "sid": session_id or _generate_session_id(),
        "classification": classification,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    })
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded, jti


def create_refresh_token(
    data: dict[str, Any],
    session_id: str = "",
) -> tuple[str, str]:
    to_encode = data.copy()
    jti = _generate_jti()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": jti,
        "iat": datetime.now(timezone.utc),
        "sid": session_id or _generate_session_id(),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    })
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded, jti


def create_token_pair(
    user_id: str,
    scopes: list[str],
    session_id: str = "",
    classification: str = "UNCLASSIFIED",
) -> SessionToken:
    sid = session_id or _generate_session_id()
    access_data = {"sub": user_id, "scopes": scopes}
    refresh_data = {"sub": user_id, "scopes": scopes}

    access_token, access_jti = create_access_token(
        access_data, session_id=sid, classification=classification,
    )
    refresh_token, refresh_jti = create_refresh_token(refresh_data, session_id=sid)

    return SessionToken(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        jti=access_jti,
        session_id=sid,
    )


def verify_token(token: str) -> TokenPayload:
    """Decode + validate signature, expiry, issuer and audience claims."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "type", "jti"]},
        )
        return TokenPayload(**payload)
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


async def verify_token_not_revoked(token_payload: TokenPayload, blacklist: Any = None) -> bool:
    """Async revocation check. Raises ValueError if the JTI is blacklisted.

    Returns True when no blacklist is provided or the token is still valid.
    """
    if blacklist is None or not token_payload.jti:
        return True
    is_revoked = await blacklist.is_blacklisted(token_payload.jti)
    if is_revoked:
        raise ValueError("Token has been revoked")
    return True


def validate_password_strength(password: str) -> list[str]:
    issues = []
    if len(password) < 12:
        issues.append("Password must be at least 12 characters")
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")
    common_passwords = ["password", "admin", "123456", "qwerty", "letmein", "atalaya"]
    if password.lower() in common_passwords:
        issues.append("Password is too common")
    return issues

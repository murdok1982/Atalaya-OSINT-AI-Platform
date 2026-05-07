from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CLASSIFICATION_LITERAL = Literal["UNCLASSIFIED", "CUI", "CONFIDENTIAL", "SECRET", "TOP_SECRET"]
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.\-]{3,64}$")
_PASSWORD_SPECIALS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


def _validate_password(v: str) -> str:
    if len(v) < 12 or len(v) > 256:
        raise ValueError("Password must be between 12 and 256 characters")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    if not any(c in _PASSWORD_SPECIALS for c in v):
        raise ValueError("Password must contain at least one special character")
    return v


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    full_name: str = Field(default="", max_length=256)
    scopes: list[str] = Field(default_factory=list, max_length=64)
    classification: CLASSIFICATION_LITERAL = "UNCLASSIFIED"
    tenant_id: str = Field(default="default", max_length=64)
    department: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("Username must be 3-64 chars: letters, digits, '_', '.', '-'")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=256)
    is_active: bool | None = None
    scopes: list[str] | None = Field(default=None, max_length=64)
    classification: CLASSIFICATION_LITERAL | None = None
    department: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    scopes: list[str]
    classification: str
    tenant_id: str
    department: str | None = None
    last_login: datetime | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0


class TokenRefresh(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)

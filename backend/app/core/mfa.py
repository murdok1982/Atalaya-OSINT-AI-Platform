"""Time-based One-Time Password (TOTP) helpers.

The user's TOTP secret is stored encrypted at rest using Fernet (AES-128 in CBC
+ HMAC-SHA256) keyed off the application's ``SECRET_KEY``. The encryption key
is derived deterministically so existing secrets remain decryptable across
restarts; rotating ``SECRET_KEY`` therefore requires re-enrolling MFA.

A short-lived ``mfa_ticket`` JWT is issued during the first leg of login to
prove the user passed password auth without yet emitting access tokens.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings

_MFA_TICKET_TTL_SECONDS = 300  # 5 minutes between password step and TOTP step
_MFA_TICKET_TYPE = "mfa_ticket"


def _fernet() -> Fernet:
    """Derive a stable Fernet key from SECRET_KEY (urlsafe base64, 32 bytes)."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def generate_secret() -> str:
    """Return a fresh base32-encoded TOTP secret."""
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def verify_code(encrypted_secret: str | None, code: str, *, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code with a 30-second window of tolerance."""
    secret = decrypt_secret(encrypted_secret)
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) not in (6, 7, 8):
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=valid_window)


def provisioning_uri(secret: str, *, account: str, issuer: str = "Atalaya") -> str:
    """Build an otpauth:// URI suitable for QR code generation by clients."""
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=issuer)


def issue_mfa_ticket(user_id: str, *, scopes: list[str] | None = None) -> str:
    """Mint a short-lived ticket asserting the user passed password auth."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": _MFA_TICKET_TYPE,
        "iat": now,
        "exp": now + timedelta(seconds=_MFA_TICKET_TTL_SECONDS),
        "jti": secrets.token_urlsafe(16),
        "scopes": scopes or [],
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_mfa_ticket(ticket: str) -> dict[str, Any]:
    """Decode and validate an MFA ticket. Raises ValueError on any failure."""
    try:
        payload = jwt.decode(ticket, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError(f"Invalid MFA ticket: {exc}") from exc
    if payload.get("type") != _MFA_TICKET_TYPE:
        raise ValueError("Wrong ticket type")
    return payload

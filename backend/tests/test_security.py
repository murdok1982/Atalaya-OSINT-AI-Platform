from __future__ import annotations

import pytest

from app.core.security import (
    get_password_hash,
    verify_password,
    validate_password_strength,
    create_token_pair,
    verify_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "TestP@ssw0rd123!"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password(self):
        hashed = get_password_hash("CorrectP@ss123!")
        assert not verify_password("WrongP@ss123!", hashed)

    def test_different_hashes(self):
        hashed1 = get_password_hash("TestP@ssw0rd123!")
        hashed2 = get_password_hash("TestP@ssw0rd123!")
        assert hashed1 != hashed2


class TestPasswordValidation:
    def test_strong_password(self):
        issues = validate_password_strength("Str0ng!P@ssw0rd")
        assert len(issues) == 0

    def test_short_password(self):
        issues = validate_password_strength("Sh0rt!")
        assert any("12 characters" in i for i in issues)

    def test_no_uppercase(self):
        issues = validate_password_strength("str0ng!p@ssw0rd")
        assert any("uppercase" in i.lower() for i in issues)

    def test_no_lowercase(self):
        issues = validate_password_strength("STR0NG!P@SSW0RD")
        assert any("lowercase" in i.lower() for i in issues)

    def test_no_digit(self):
        issues = validate_password_strength("Strong!Password")
        assert any("digit" in i.lower() for i in issues)

    def test_no_special(self):
        issues = validate_password_strength("Str0ngPassword123")
        assert any("special" in i.lower() for i in issues)

    def test_common_password(self):
        issues = validate_password_strength("password")
        assert any("common" in i.lower() for i in issues)


class TestTokenPair:
    def test_create_token_pair(self):
        pair = create_token_pair(user_id="test-user-123", scopes=["read:cases"])
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0
        assert pair.jti
        assert pair.session_id

    def test_verify_access_token(self):
        pair = create_token_pair(user_id="test-user-123", scopes=["read:cases", "write:cases"])
        payload = verify_token(pair.access_token)
        assert payload.sub == "test-user-123"
        assert "read:cases" in payload.scopes
        assert "write:cases" in payload.scopes
        assert payload.type == "access"

    def test_verify_refresh_token(self):
        pair = create_token_pair(user_id="test-user-123", scopes=["read:cases"])
        payload = verify_token(pair.refresh_token)
        assert payload.sub == "test-user-123"
        assert payload.type == "refresh"

    def test_invalid_token(self):
        with pytest.raises(ValueError, match="Invalid token"):
            verify_token("invalid.token.here")

    def test_unique_jti(self):
        pair1 = create_token_pair(user_id="user-1", scopes=[])
        pair2 = create_token_pair(user_id="user-2", scopes=[])
        assert pair1.jti != pair2.jti

    def test_session_persistence(self):
        pair = create_token_pair(user_id="user-1", session_id="custom-session-123")
        assert pair.session_id == "custom-session-123"

from __future__ import annotations

import time

import pytest

from app.core.bruteforce import BruteForceProtector


class TestBruteForceProtector:
    def setup_method(self):
        BruteForceProtector._attempts.clear()
        BruteForceProtector._ip_attempts.clear()

    def test_no_lock_on_fresh_account(self):
        assert not BruteForceProtector.is_locked("new_user")

    def test_lock_after_max_attempts(self):
        for _ in range(BruteForceProtector.MAX_ATTEMPTS):
            BruteForceProtector.record_failure("test_user", "127.0.0.1")
        assert BruteForceProtector.is_locked("test_user")

    def test_remaining_attempts(self):
        BruteForceProtector.record_failure("test_user")
        assert BruteForceProtector.get_remaining_attempts("test_user") == 4

    def test_success_resets_counter(self):
        BruteForceProtector.record_failure("test_user", "127.0.0.1")
        BruteForceProtector.record_success("test_user", "127.0.0.1")
        assert not BruteForceProtector.is_locked("test_user")
        assert BruteForceProtector.get_remaining_attempts("test_user") == 5

    def test_ip_block_after_max_attempts(self):
        for _ in range(BruteForceProtector.IP_MAX_ATTEMPTS):
            BruteForceProtector.record_failure(f"user_{_}", "10.0.0.1")
        assert BruteForceProtector.is_ip_blocked("10.0.0.1")

    def test_progressive_lockout(self):
        for _ in range(BruteForceProtector.MAX_ATTEMPTS * 2):
            BruteForceProtector.record_failure("progressive_user")
        assert BruteForceProtector.is_locked("progressive_user")

    def test_cleanup_expired(self):
        BruteForceProtector._attempts["expired_user"] = type(
            "AttemptRecord", (), {"locked_until": time.time() - 100, "count": 0}
        )()
        removed = BruteForceProtector.cleanup_expired()
        assert removed >= 1

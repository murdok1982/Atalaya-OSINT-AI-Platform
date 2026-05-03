from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["version"] == "2.0.0"


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_invalid(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "wrong",
        })
        assert response.status_code in (401, 429)

    @pytest.mark.asyncio
    async def test_login_empty(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient, mock_user_data: dict):
        response = await client.post("/api/v1/auth/register", json=mock_user_data)
        assert response.status_code in (201, 400)

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "username": "weakuser",
            "email": "weak@test.com",
            "password": "123",
        })
        assert response.status_code == 400


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client: AsyncClient):
        response = await client.get("/")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_waf_headers(self, client: AsyncClient):
        response = await client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Strict-Transport-Security")

    @pytest.mark.asyncio
    async def test_no_server_header(self, client: AsyncClient):
        response = await client.get("/")
        assert "Server" not in response.headers


class TestCaseEndpoints:
    @pytest.mark.asyncio
    async def test_cases_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/cases/")
        assert response.status_code == 401


class TestJobEndpoints:
    @pytest.mark.asyncio
    async def test_jobs_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/jobs/")
        assert response.status_code == 401


class TestEvidenceEndpoints:
    @pytest.mark.asyncio
    async def test_evidence_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/evidence/")
        assert response.status_code == 401

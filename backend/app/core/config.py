from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET = "CHANGE_ME_in_production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = _INSECURE_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Server
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    FRONTEND_PORT: int = 3000
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://atalaya_user:atalaya_pass@localhost:5432/atalaya_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "atalaya_evidence"

    # LLM
    LLM_DEFAULT_PROVIDER: str = "ollama"
    LLM_DEFAULT_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.1"
    OPENAI_API_KEY: str = ""
    OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_DEFAULT_MODEL: str = "claude-haiku-4-5-20251001"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_DEFAULT_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    LLM_FALLBACK_CHAIN: list[str] = ["ollama", "openai", "anthropic", "openrouter"]

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_CHATS: list[int] = []

    # Storage
    EVIDENCE_STORAGE_PATH: str = "./data/evidence"
    REPORTS_STORAGE_PATH: str = "./data/reports"
    LOGS_PATH: str = "./data/logs"

    # Security limits
    MAX_FILE_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 60

    # Optional integrations
    SHODAN_API_KEY: str = ""
    VIRUSTOTAL_API_KEY: str = ""
    HUNTER_IO_API_KEY: str = ""
    URLSCAN_API_KEY: str = ""
    IPINFO_TOKEN: str = ""
    SECURITYTRAILS_API_KEY: str = ""
    HIBP_API_KEY: str = ""

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_str_list(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("TELEGRAM_ALLOWED_CHATS", mode="before")
    @classmethod
    def parse_telegram_chats(cls, v: str | list) -> list[int]:
        if isinstance(v, str) and v:
            return [int(c.strip()) for c in v.split(",") if c.strip()]
        if isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == _INSECURE_SECRET:
            raise ValueError(
                "SECRET_KEY must be changed from the default value before running in production. "
                "Generate one with: python scripts/generate_keys.py"
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

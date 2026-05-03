from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET = "CHANGE_ME_in_production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "Atalaya OSINT Platform"
    APP_VERSION: str = "2.0.0"
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
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 50

    # Neo4j (Graph Database)
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "atalaya_evidence"
    QDRANT_EMBEDDING_DIM: int = 1536

    # Kafka / Event Streaming
    KAFKA_BOOTSTRAP_SERVERS: str = ""
    KAFKA_EVENTS_TOPIC: str = "atalaya-events"
    KAFKA_ALERTS_TOPIC: str = "atalaya-alerts"
    KAFKA_CONSUMER_GROUP: str = "atalaya-backend"

    # LLM
    LLM_DEFAULT_PROVIDER: str = "ollama"
    LLM_DEFAULT_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.1"
    OLLAMA_ENABLED: bool = True
    OPENAI_API_KEY: str = ""
    OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_DEFAULT_MODEL: str = "claude-haiku-4-5-20251001"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_DEFAULT_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    LLM_FALLBACK_CHAIN: list[str] = ["ollama", "openai", "anthropic", "openrouter"]
    LLM_MAX_RETRIES: int = 3
    LLM_REQUEST_TIMEOUT: int = 120

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ALLOWED_CHATS: list[int] = []

    # Storage
    EVIDENCE_STORAGE_PATH: str = "./data/evidence"
    REPORTS_STORAGE_PATH: str = "./data/reports"
    LOGS_PATH: str = "./data/logs"

    # Security
    MAX_FILE_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_API_PER_MINUTE: int = 120
    RATE_LIMIT_LOGIN_PER_HOUR: int = 10
    BRUTE_FORCE_MAX_ATTEMPTS: int = 5
    BRUTE_FORCE_LOCKOUT_SECONDS: int = 300
    BRUTE_FORCE_IP_MAX_ATTEMPTS: int = 20
    BRUTE_FORCE_IP_LOCKOUT_SECONDS: int = 900
    PASSWORD_MIN_LENGTH: int = 12
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_CONCURRENT_SESSIONS: int = 5
    ENABLE_MTLS: bool = False
    MTLS_CA_CERT_PATH: str = ""
    ENABLE_WAF_HEADERS: bool = True
    ENABLE_CSRF: bool = False

    # Secret Rotation
    SECRET_ROTATION_HOURS: int = 72
    AUTO_ROTATE_API_KEYS: bool = False

    # Audit
    AUDIT_HASH_CHAIN: bool = True
    AUDIT_WORM_STORAGE: bool = False
    AUDIT_RETENTION_DAYS: int = 3650

    # Classification
    DEFAULT_CLASSIFICATION: str = "UNCLASSIFIED"
    CLASSIFICATION_LABELS: list[str] = ["UNCLASSIFIED", "CUI", "CONFIDENTIAL", "SECRET", "TOP_SECRET"]

    # Observability
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "atalaya-backend"
    PROMETHEUS_ENABLED: bool = False
    PROMETHEUS_PORT: int = 9090

    # Backup
    BACKUP_ENABLED: bool = False
    BACKUP_SCHEDULE: str = "0 2 * * *"
    BACKUP_S3_ENDPOINT: str = ""
    BACKUP_S3_BUCKET: str = ""
    BACKUP_S3_ACCESS_KEY: str = ""
    BACKUP_S3_SECRET_KEY: str = ""
    BACKUP_RETENTION_DAYS: int = 90

    # Optional integrations
    SHODAN_API_KEY: str = ""
    VIRUSTOTAL_API_KEY: str = ""
    HUNTER_IO_API_KEY: str = ""
    URLSCAN_API_KEY: str = ""
    IPINFO_TOKEN: str = ""
    SECURITYTRAILS_API_KEY: str = ""
    HIBP_API_KEY: str = ""
    CENSYS_API_ID: str = ""
    CENSYS_API_SECRET: str = ""

    # Dark Web
    TOR_PROXY_URL: str = "socks5://127.0.0.1:9050"
    DARK_WEB_ENABLED: bool = False

    # GEOINT
    SENTINEL_HUB_CLIENT_ID: str = ""
    SENTINEL_HUB_CLIENT_SECRET: str = ""
    MAPBOX_TOKEN: str = ""

    # FININT
    BLOCKCHAIN_API_KEY: str = ""
    ETHERSCAN_API_KEY: str = ""

    # Cyber Threat Intelligence
    MISP_URL: str = ""
    MISP_API_KEY: str = ""
    OTX_API_KEY: str = ""
    VULN_INTEL_API_KEY: str = ""

    # STIX/TAXII
    TAXII_SERVER_URL: str = ""
    TAXII_USERNAME: str = ""
    TAXII_PASSWORD: str = ""

    # Multi-tenant
    MULTI_TENANT: bool = False
    DEFAULT_TENANT_ID: str = "default"

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_str_list(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("TELEGRAM_ALLOWED_CHATS", "LLM_FALLBACK_CHAIN", "CLASSIFICATION_LABELS", mode="before")
    @classmethod
    def parse_list_str(cls, v: str | list) -> list[str]:
        if isinstance(v, str) and v:
            return [c.strip() for c in v.split(",") if c.strip()]
        if isinstance(v, list):
            return v
        return []

    @field_validator("TELEGRAM_ALLOWED_CHATS", mode="before")
    @classmethod
    def parse_telegram_chats(cls, v: str | list) -> list[int]:
        if isinstance(v, str) and v:
            return [int(c.strip()) for c in v.split(",") if c.strip()]
        if isinstance(v, list):
            return [int(c) for c in v]
        return []

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == _INSECURE_SECRET:
            raise ValueError(
                "SECRET_KEY must be changed from the default value before running in production. "
                "Generate one with: python scripts/generate_keys.py"
            )
        if self.ENVIRONMENT == "production" and len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return self

    @model_validator(mode="after")
    def generate_secret_if_missing(self) -> Self:
        if self.SECRET_KEY == _INSECURE_SECRET and self.ENVIRONMENT == "development":
            object.__setattr__(self, "SECRET_KEY", secrets.token_urlsafe(64))
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def has_graph_db(self) -> bool:
        return bool(self.NEO4J_URI and self.NEO4J_USERNAME and self.NEO4J_PASSWORD)

    @property
    def has_kafka(self) -> bool:
        return bool(self.KAFKA_BOOTSTRAP_SERVERS)

    @property
    def has_otel(self) -> bool:
        return self.OTEL_ENABLED and bool(self.OTEL_ENDPOINT)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

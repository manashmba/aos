"""
AOS Core Configuration
Centralized settings management using pydantic-settings.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "AOS"
    app_env: str = "development"
    app_debug: bool = False
    app_version: str = "0.1.0"
    secret_key: str = "change-me-in-production"
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://aos_user:aos_password@localhost:5432/aos_db"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    primary_llm_model: str = "claude-sonnet-4-6"
    fallback_llm_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1

    # WhatsApp
    whatsapp_api_url: str = "https://graph.facebook.com/v21.0"
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_bot_url: str = ""          # HTTP bridge to the aos-whatsapp-bot service
    whatsapp_bot_token: str = ""        # Shared secret for /notify/* calls

    # GST
    gst_api_url: str = ""
    gst_api_key: str = ""
    e_invoice_api_url: str = ""
    e_invoice_username: str = ""
    e_invoice_password: str = ""

    # Banking
    bank_api_url: str = ""
    bank_api_key: str = ""

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-south-1"
    s3_bucket_name: str = "aos-documents"

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@aos.app"

    # OCR
    ocr_provider: str = "textract"

    # Observability
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

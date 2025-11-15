"""
Application Settings
Centralized configuration management
"""
import os
from typing import Optional
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        BaseSettings = None


class Settings(BaseSettings if BaseSettings else object):
    """Application settings"""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # OpenAI Configuration
    openai_api_key: Optional[str] = None

    # Database Configuration
    database_url: str = "postgresql://user:password@localhost:5432/paperpulse"
    redis_url: str = "redis://localhost:6379/0"

    # LightRAG Configuration
    lightrag_working_dir: str = "./data/lightrag"
    lightrag_llm_model: str = "gpt-4o-mini"
    lightrag_embedding_model: str = "text-embedding-3-small"

    # Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

    # Slack Configuration
    slack_webhook_url: Optional[str] = None

    # Storage Configuration
    s3_bucket_name: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Feature Flags
    enable_knowledge_graph: bool = True
    enable_recommendations: bool = True
    enable_chatbot: bool = True

    if BaseSettings:
        class Config:
            env_file = ".env"
            case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    if BaseSettings:
        return Settings()
    else:
        # Fallback if pydantic not available
        settings = Settings()
        # Manually load from environment
        for field in dir(settings):
            if not field.startswith('_'):
                env_value = os.getenv(field.upper())
                if env_value is not None:
                    setattr(settings, field, env_value)
        return settings

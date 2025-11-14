"""Application configuration"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "PaperPulse"
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    secret_key: str = Field(..., alias="SECRET_KEY")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(..., alias="REDIS_URL")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # JWT
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # API Keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    semantic_scholar_api_key: Optional[str] = Field(
        default=None, alias="SEMANTIC_SCHOLAR_API_KEY"
    )

    # External APIs
    arxiv_api_base_url: str = Field(
        default="http://export.arxiv.org/api/query",
        alias="ARXIV_API_BASE_URL",
    )

    # Embedding Model
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1024, alias="EMBEDDING_DIMENSION")
    embedding_device: str = Field(default="cpu", alias="EMBEDDING_DEVICE")

    # File Storage
    pdf_storage_path: str = Field(default="/app/uploads/pdfs", alias="PDF_STORAGE_PATH")
    max_upload_size: int = Field(default=52428800, alias="MAX_UPLOAD_SIZE")  # 50MB

    # Celery
    celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., alias="CELERY_RESULT_BACKEND")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.app_env == "production"


# Global settings instance
settings = Settings()

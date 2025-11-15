"""
Application configuration management using Pydantic Settings
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "PaperPulse"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    secret_key: str = Field(..., min_length=32)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str = Field(..., description="PostgreSQL connection URL")
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_db: int = 0
    redis_celery_broker_db: int = 1
    redis_celery_backend_db: int = 2

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 3600

    # Object Storage (S3/MinIO)
    s3_endpoint_url: Optional[str] = None
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "paperpulse-pdfs"
    s3_region: str = "us-east-1"

    # External APIs
    arxiv_max_results: int = 100
    arxiv_rate_limit_delay: float = 3.0

    semantic_scholar_api_key: Optional[str] = None

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_retries: int = 3

    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Embedding Models
    bge_model_name: str = "BAAI/bge-m3"
    bge_model_cache_dir: str = "./models/bge-m3"
    bge_use_fp16: bool = True
    bge_device: str = "cuda"

    # Vector Search
    vector_search_hnsw_m: int = 16
    vector_search_hnsw_ef_construction: int = 64
    vector_search_ef_search: int = 40

    # PDF Processing
    pdf_max_pages: int = 100
    pdf_ocr_enabled: bool = True
    pdf_ocr_language: str = "eng"
    tesseract_cmd: str = "/usr/bin/tesseract"

    # Knowledge Graph
    lightrag_working_dir: str = "./data/lightrag"
    spacy_model: str = "en_core_sci_lg"

    # Notification
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: str = "noreply@paperpulse.ai"
    smtp_from_name: str = "PaperPulse"

    slack_webhook_url: Optional[str] = None
    slack_bot_token: Optional[str] = None

    # Monitoring
    prometheus_port: int = 9090
    grafana_port: int = 3000

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "./logs/app.log"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # Feature Flags
    enable_knowledge_graph: bool = True
    enable_notifications: bool = True
    enable_recommendations: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """Check if environment is production"""
        return self.environment.lower() == "production"

    @property
    def redis_cache_url(self) -> str:
        """Get Redis cache URL"""
        return f"redis://localhost:6379/{self.redis_cache_db}"

    @property
    def async_database_url(self) -> str:
        """Get async database URL"""
        return self.database_url

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic"""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


# Global settings instance
settings = Settings()

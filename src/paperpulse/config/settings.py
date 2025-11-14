"""Application configuration settings."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "PaperPulse"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 3600

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # S3 / MinIO
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_REGION: str = "us-east-1"

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4.5"

    # BGE Embeddings
    BGE_MODEL_NAME: str = "BAAI/bge-m3"
    BGE_DEVICE: str = "cpu"
    BGE_MAX_LENGTH: int = 8192

    # arXiv
    ARXIV_MAX_RESULTS: int = 100
    ARXIV_QUERY_INTERVAL: int = 3

    # Semantic Scholar
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    SEMANTIC_SCHOLAR_RATE_LIMIT: int = 100

    # Papers with Code
    PAPERS_WITH_CODE_API_KEY: str = ""

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@paperpulse.ai"

    # Slack
    SLACK_WEBHOOK_URL: str = ""
    SLACK_BOT_TOKEN: str = ""

    # Monitoring
    PROMETHEUS_PORT: int = 9090
    ENABLE_METRICS: bool = True

    # LightRAG
    LIGHTRAG_WORKING_DIR: str = "./data/lightrag"
    LIGHTRAG_KG_EXTRACT_MAX_WORKERS: int = 4

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Feature Flags
    ENABLE_KNOWLEDGE_GRAPH: bool = True
    ENABLE_RECOMMENDATIONS: bool = True
    ENABLE_CHATBOT: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

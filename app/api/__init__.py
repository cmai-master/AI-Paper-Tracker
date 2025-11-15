"""
API Module - FastAPI routes
"""

from app.api import ingestion, pdf, embedding, search

__all__ = ["ingestion", "pdf", "embedding", "search"]

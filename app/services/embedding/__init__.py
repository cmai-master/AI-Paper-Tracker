"""
Embedding & Vector Store Module

Complete embedding pipeline and vector search functionality
"""

from app.services.embedding.embedder import BGEM3Embedder, get_embedder
from app.services.embedding.chunker import TextChunker, create_chunker
from app.services.embedding.processor import EmbeddingProcessor
from app.services.embedding.search import VectorSearchService
from app.services.embedding.schemas import (
    SearchQuery,
    SearchResult,
    SearchResponse,
    EmbeddingStats,
    ChunkingStrategy,
    TextChunk,
    EmbeddingResult,
)

__all__ = [
    # Embedder
    "BGEM3Embedder",
    "get_embedder",
    # Chunker
    "TextChunker",
    "create_chunker",
    # Processor
    "EmbeddingProcessor",
    # Search
    "VectorSearchService",
    # Schemas
    "SearchQuery",
    "SearchResult",
    "SearchResponse",
    "EmbeddingStats",
    "ChunkingStrategy",
    "TextChunk",
    "EmbeddingResult",
]

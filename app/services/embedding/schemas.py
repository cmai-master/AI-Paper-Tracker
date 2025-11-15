"""
Embedding Service Schemas
"""

from typing import List, Dict, Optional, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DenseVector(BaseModel):
    """Dense vector representation"""

    model_config = ConfigDict(from_attributes=True)

    vector: List[float] = Field(..., description="Dense embedding vector")
    dimension: int = Field(..., description="Vector dimension")


class SparseVector(BaseModel):
    """Sparse vector representation (indices + values)"""

    model_config = ConfigDict(from_attributes=True)

    indices: List[int] = Field(..., description="Non-zero indices")
    values: List[float] = Field(..., description="Non-zero values")
    dimension: int = Field(..., description="Total vector dimension")


class EmbeddingResult(BaseModel):
    """Result of embedding generation"""

    model_config = ConfigDict(from_attributes=True)

    dense_vector: Optional[List[float]] = Field(None, description="Dense embedding")
    sparse_vector: Optional[Dict[str, List]] = Field(
        None, description="Sparse embedding (indices + values)"
    )
    model_name: str = Field(..., description="Model used for embedding")
    embedding_version: str = Field(default="1.0", description="Embedding version")
    generation_time_ms: int = Field(..., description="Time taken to generate embedding")


class TextChunk(BaseModel):
    """A chunk of text for embedding"""

    model_config = ConfigDict(from_attributes=True)

    text: str = Field(..., description="Chunk text")
    chunk_index: int = Field(..., description="Order in document")
    chunk_size: int = Field(..., description="Character count")
    word_count: int = Field(..., description="Word count")
    section_type: Optional[str] = Field(None, description="Section this belongs to")
    section_title: Optional[str] = Field(None, description="Section title")
    page_number: Optional[int] = Field(None, description="Page number")


class ChunkingStrategy(BaseModel):
    """Configuration for text chunking"""

    model_config = ConfigDict(from_attributes=True)

    strategy: Literal["fixed", "semantic", "sliding"] = Field(
        default="semantic", description="Chunking strategy"
    )
    chunk_size: int = Field(default=512, description="Target chunk size (tokens)")
    chunk_overlap: int = Field(default=50, description="Overlap between chunks")
    min_chunk_size: int = Field(
        default=100, description="Minimum chunk size to keep"
    )


class EmbeddingMetadata(BaseModel):
    """Metadata for embeddings"""

    model_config = ConfigDict(from_attributes=True)

    paper_id: UUID
    document_id: Optional[UUID] = None
    model_name: str = "BAAI/bge-m3"
    embedding_version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaperEmbeddingData(BaseModel):
    """Data for creating paper embedding"""

    model_config = ConfigDict(from_attributes=True)

    paper_id: UUID
    title: str
    abstract: str
    dense_vector: Optional[List[float]] = None
    sparse_vector: Optional[Dict] = None
    text_hash: str
    model_name: str = "BAAI/bge-m3"


class ChunkEmbeddingData(BaseModel):
    """Data for creating chunk embedding"""

    model_config = ConfigDict(from_attributes=True)

    paper_id: UUID
    document_id: UUID
    chunk_index: int
    chunk_text: str
    chunk_size: int
    word_count: int
    section_type: Optional[str] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    dense_vector: Optional[List[float]] = None
    sparse_vector: Optional[Dict] = None
    model_name: str = "BAAI/bge-m3"


class SectionEmbeddingData(BaseModel):
    """Data for creating section embedding"""

    model_config = ConfigDict(from_attributes=True)

    paper_id: UUID
    document_id: UUID
    section_id: UUID
    section_type: str
    section_title: Optional[str] = None
    section_text: str
    word_count: int
    dense_vector: Optional[List[float]] = None
    sparse_vector: Optional[Dict] = None
    model_name: str = "BAAI/bge-m3"


class SearchQuery(BaseModel):
    """Search query with options"""

    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., description="Search query text")
    search_type: Literal["dense", "sparse", "hybrid"] = Field(
        default="hybrid", description="Type of search"
    )
    top_k: int = Field(default=10, description="Number of results to return", ge=1, le=100)
    min_score: Optional[float] = Field(
        None, description="Minimum similarity score", ge=0.0, le=1.0
    )
    filter_section_types: Optional[List[str]] = Field(
        None, description="Filter by section types"
    )
    filter_paper_ids: Optional[List[UUID]] = Field(
        None, description="Filter by paper IDs"
    )
    rerank: bool = Field(default=False, description="Apply reranking")


class SearchResult(BaseModel):
    """Single search result"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Embedding ID")
    paper_id: UUID = Field(..., description="Paper ID")
    text: str = Field(..., description="Matched text")
    score: float = Field(..., description="Similarity score")
    section_type: Optional[str] = Field(None, description="Section type")
    section_title: Optional[str] = Field(None, description="Section title")
    chunk_index: Optional[int] = Field(None, description="Chunk index if applicable")

    # Paper metadata (joined)
    paper_title: Optional[str] = None
    paper_authors: Optional[List[str]] = None
    arxiv_id: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response with results"""

    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., description="Original query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    search_type: str = Field(..., description="Type of search performed")
    search_time_ms: int = Field(..., description="Time taken for search")


class EmbeddingStats(BaseModel):
    """Statistics about embeddings"""

    model_config = ConfigDict(from_attributes=True)

    total_paper_embeddings: int = 0
    total_chunk_embeddings: int = 0
    total_section_embeddings: int = 0
    total_entity_embeddings: int = 0
    avg_chunks_per_paper: float = 0.0
    model_name: str = "BAAI/bge-m3"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class BatchEmbeddingRequest(BaseModel):
    """Request for batch embedding generation"""

    model_config = ConfigDict(from_attributes=True)

    texts: List[str] = Field(..., description="List of texts to embed")
    batch_size: int = Field(default=32, description="Batch size for processing")
    show_progress: bool = Field(default=True, description="Show progress bar")


class BatchEmbeddingResponse(BaseModel):
    """Response for batch embedding generation"""

    model_config = ConfigDict(from_attributes=True)

    dense_vectors: List[List[float]] = Field(..., description="Dense embeddings")
    sparse_vectors: Optional[List[Dict]] = Field(
        None, description="Sparse embeddings"
    )
    total_processed: int = Field(..., description="Total texts processed")
    total_time_ms: int = Field(..., description="Total processing time")
    model_name: str = Field(..., description="Model used")

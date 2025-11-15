"""
Embedding Models - Vector embeddings for semantic search
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, Text, Integer, Float, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class PaperEmbedding(Base):
    """
    Paper-level embeddings (abstract + title)

    Used for high-level paper similarity search
    """

    __tablename__ = "paper_embeddings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    paper_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), unique=True
    )

    # Embeddings (BGE-M3: 1024-dim dense + sparse)
    dense_vector: Mapped[Optional[list]] = mapped_column(
        Vector(1024), nullable=True
    )  # Dense embedding
    sparse_vector: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )  # Sparse embedding (indices + values)

    # Source text
    source_text: Mapped[str] = mapped_column(Text, nullable=False)  # Title + Abstract
    text_hash: Mapped[str] = mapped_column(
        String(64), index=True
    )  # SHA-256 for deduplication

    # Metadata
    model_name: Mapped[str] = mapped_column(String(100), default="BAAI/bge-m3")
    embedding_version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    paper = relationship("Paper", backref="embedding")

    __table_args__ = (
        # HNSW index for fast approximate nearest neighbor search
        Index(
            "idx_paper_embedding_dense_hnsw",
            "dense_vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"dense_vector": "vector_cosine_ops"},
        ),
        Index("idx_paper_embedding_text_hash", "text_hash"),
    )


class ChunkEmbedding(Base):
    """
    Text chunk embeddings for fine-grained search

    Used for detailed content retrieval within papers
    """

    __tablename__ = "chunk_embeddings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("processed_documents.id", ondelete="CASCADE"),
        index=True,
    )
    paper_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )

    # Chunk information
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Order in document
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer)  # Character count
    word_count: Mapped[int] = mapped_column(Integer)

    # Context
    section_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # Which section this belongs to
    section_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Embeddings
    dense_vector: Mapped[Optional[list]] = mapped_column(Vector(1024), nullable=True)
    sparse_vector: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    model_name: Mapped[str] = mapped_column(String(100), default="BAAI/bge-m3")
    embedding_version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("ProcessedDocument", backref="chunk_embeddings")
    paper = relationship("Paper")

    __table_args__ = (
        # HNSW index for vector search
        Index(
            "idx_chunk_embedding_dense_hnsw",
            "dense_vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"dense_vector": "vector_cosine_ops"},
        ),
        # Composite index for document queries
        Index("idx_chunk_document_index", "document_id", "chunk_index"),
        Index("idx_chunk_paper_id", "paper_id"),
    )


class SectionEmbedding(Base):
    """
    Section-level embeddings (abstract, intro, method, etc.)

    Used for section-specific search and comparison
    """

    __tablename__ = "section_embeddings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    section_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("document_sections.id", ondelete="CASCADE"),
        unique=True,
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("processed_documents.id", ondelete="CASCADE"),
        index=True,
    )
    paper_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )

    # Section info
    section_type: Mapped[str] = mapped_column(String(50), index=True)
    section_title: Mapped[Optional[str]] = mapped_column(String(500))
    section_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer)

    # Embeddings
    dense_vector: Mapped[Optional[list]] = mapped_column(Vector(1024), nullable=True)
    sparse_vector: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    model_name: Mapped[str] = mapped_column(String(100), default="BAAI/bge-m3")
    embedding_version: Mapped[str] = mapped_column(String(20), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    section = relationship("DocumentSection", backref="embedding")
    document = relationship("ProcessedDocument")
    paper = relationship("Paper")

    __table_args__ = (
        # HNSW index for vector search
        Index(
            "idx_section_embedding_dense_hnsw",
            "dense_vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"dense_vector": "vector_cosine_ops"},
        ),
        # Index for section type filtering
        Index("idx_section_embedding_type", "section_type"),
    )


class EntityEmbedding(Base):
    """
    Entity embeddings for knowledge graph nodes

    Future use: Named entities, concepts, methods extracted from papers
    """

    __tablename__ = "entity_embeddings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    paper_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )

    # Entity information
    entity_name: Mapped[str] = mapped_column(String(500), index=True)
    entity_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # method, dataset, metric, person, org, etc.
    entity_context: Mapped[str] = mapped_column(
        Text
    )  # Surrounding text for context
    normalized_name: Mapped[str] = mapped_column(
        String(500), index=True
    )  # Lowercase, normalized

    # Embeddings
    dense_vector: Mapped[Optional[list]] = mapped_column(Vector(1024), nullable=True)
    sparse_vector: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # Entity extraction confidence
    mention_count: Mapped[int] = mapped_column(
        Integer, default=1
    )  # How many times mentioned
    model_name: Mapped[str] = mapped_column(String(100), default="BAAI/bge-m3")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    paper = relationship("Paper")

    __table_args__ = (
        # HNSW index for vector search
        Index(
            "idx_entity_embedding_dense_hnsw",
            "dense_vector",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"dense_vector": "vector_cosine_ops"},
        ),
        # Index for entity lookup
        Index("idx_entity_name", "entity_name"),
        Index("idx_entity_normalized_name", "normalized_name"),
        Index("idx_entity_type", "entity_type"),
    )

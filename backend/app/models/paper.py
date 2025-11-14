"""Paper-related database models"""

from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Paper(Base):
    """Core paper metadata"""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    arxiv_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    categories: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    # Publication dates
    published_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    updated_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # External IDs
    doi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    semantic_scholar_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metrics
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    influential_citation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    processed_documents: Mapped[List["ProcessedDocument"]] = relationship(
        "ProcessedDocument", back_populates="paper", cascade="all, delete-orphan"
    )
    paper_embeddings: Mapped[List["PaperEmbedding"]] = relationship(
        "PaperEmbedding", back_populates="paper", cascade="all, delete-orphan"
    )
    chunk_embeddings: Mapped[List["ChunkEmbedding"]] = relationship(
        "ChunkEmbedding", back_populates="paper", cascade="all, delete-orphan"
    )
    extracted_references: Mapped[List["ExtractedReference"]] = relationship(
        "ExtractedReference",
        foreign_keys="ExtractedReference.source_paper_id",
        back_populates="source_paper",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_papers_published_date", published_date.desc()),
        Index("idx_papers_categories", categories, postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Paper(arxiv_id={self.arxiv_id}, title={self.title[:50]})>"


class ProcessedDocument(Base):
    """Processed PDF document content"""

    __tablename__ = "processed_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Content
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[dict] = mapped_column(JSON, nullable=False)  # {title: content}
    tables: Mapped[List[dict]] = mapped_column(JSON, default=list)
    figures: Mapped[List[dict]] = mapped_column(JSON, default=list)

    # Metadata
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pymupdf, pdfplumber, etc.

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="processed_documents")

    def __repr__(self) -> str:
        return f"<ProcessedDocument(paper_id={self.paper_id}, pages={self.page_count})>"


class PaperEmbedding(Base):
    """Paper-level embeddings"""

    __tablename__ = "paper_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Embedding vectors
    title_embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(1024), nullable=True
    )  # BGE-M3 dimension
    abstract_embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(1024), nullable=True
    )

    # Embedding metadata
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="paper_embeddings")

    __table_args__ = (
        Index(
            "idx_paper_embeddings_title",
            "title_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
        Index(
            "idx_paper_embeddings_abstract",
            "abstract_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )

    def __repr__(self) -> str:
        return f"<PaperEmbedding(paper_id={self.paper_id}, model={self.model_name})>"


class ChunkEmbedding(Base):
    """Document chunk embeddings for fine-grained retrieval"""

    __tablename__ = "chunk_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Chunk content
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Embedding
    embedding: Mapped[Vector] = mapped_column(Vector(1024), nullable=False)

    # Metadata
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="chunk_embeddings")

    __table_args__ = (
        Index("idx_chunk_paper_index", paper_id, chunk_index),
        Index(
            "idx_chunk_embeddings_vector",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )

    def __repr__(self) -> str:
        return f"<ChunkEmbedding(paper_id={self.paper_id}, chunk={self.chunk_index})>"


class ExtractedReference(Base):
    """References extracted from papers"""

    __tablename__ = "extracted_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Reference metadata
    reference_text: Mapped[str] = mapped_column(Text, nullable=False)
    reference_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reference_arxiv_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    reference_doi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Matched paper (if exists in our DB)
    target_paper_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    source_paper: Mapped["Paper"] = relationship(
        "Paper", foreign_keys=[source_paper_id], back_populates="extracted_references"
    )

    def __repr__(self) -> str:
        return f"<ExtractedReference(source={self.source_paper_id}, target={self.target_paper_id})>"

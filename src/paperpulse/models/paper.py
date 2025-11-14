"""Paper and document models."""

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

from paperpulse.db.base import Base


class Paper(Base):
    """Main paper entity."""

    __tablename__ = "papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identifiers
    arxiv_id = Column(String(50), unique=True, index=True)
    doi = Column(String(100), unique=True, index=True, nullable=True)
    semantic_scholar_id = Column(String(100), index=True, nullable=True)

    # Basic metadata
    title = Column(Text, nullable=False, index=True)
    abstract = Column(Text)
    authors = Column(ARRAY(String), nullable=False)

    # Publication info
    published_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime)
    journal = Column(String(255))
    venue = Column(String(255))

    # Categories and tags
    categories = Column(ARRAY(String))  # arXiv categories
    primary_category = Column(String(50), index=True)

    # URLs and references
    pdf_url = Column(Text)
    source_url = Column(Text)  # Original source (arXiv, etc.)

    # Metrics
    citation_count = Column(Integer, default=0)
    references_count = Column(Integer, default=0)

    # Rich metadata from external sources
    semantic_scholar_data = Column(JSONB)  # Extra data from Semantic Scholar
    papers_with_code_data = Column(JSONB)  # Code implementations, benchmarks

    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    processed_document = relationship("ProcessedDocument", back_populates="paper", uselist=False)
    embeddings = relationship("PaperEmbedding", back_populates="paper")
    chunks = relationship("ChunkEmbedding", back_populates="paper")
    kg_entity_associations = relationship("KGEntityPaper", back_populates="paper")
    references = relationship("ExtractedReference", back_populates="paper")
    recommendations = relationship("Recommendation", back_populates="paper")
    user_interactions = relationship("UserInteraction", back_populates="paper")


class ProcessedDocument(Base):
    """Processed document content from PDF."""

    __tablename__ = "processed_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, unique=True)

    # Full text content
    full_text = Column(Text)

    # Structured sections
    sections = Column(JSONB)  # {section_name: text, ...}

    # Extracted elements
    tables = Column(JSONB)  # List of extracted tables
    figures = Column(JSONB)  # List of figure metadata
    equations = Column(JSONB)  # List of extracted equations

    # Parsed content
    parsed_references = Column(JSONB)  # Bibliography entries
    key_phrases = Column(ARRAY(String))  # Extracted key phrases

    # Processing metadata
    parser_used = Column(String(50))  # pymupdf, pdfplumber, etc.
    word_count = Column(Integer)
    page_count = Column(Integer)

    # Storage info
    pdf_s3_key = Column(String(255))  # S3 key for PDF file
    pdf_hash = Column(String(64))  # SHA-256 hash for deduplication

    # Timestamps
    processed_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    paper = relationship("Paper", back_populates="processed_document")


class PaperEmbedding(Base):
    """Paper-level embeddings."""

    __tablename__ = "paper_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True)

    # Embedding type
    embedding_type = Column(String(50), nullable=False)  # title, abstract, full_text
    model_name = Column(String(100), nullable=False)  # BGE-M3, OpenAI, etc.

    # Dense and sparse vectors
    dense_vector = Column(Vector(1024))  # Adjust dimension based on model
    sparse_vector = Column(JSONB)  # For sparse representations (BM25, SPLADE)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    paper = relationship("Paper", back_populates="embeddings")


class ChunkEmbedding(Base):
    """Chunk-level embeddings for fine-grained retrieval."""

    __tablename__ = "chunk_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True)

    # Chunk info
    chunk_index = Column(Integer, nullable=False)  # Order in document
    chunk_text = Column(Text, nullable=False)
    chunk_type = Column(String(50))  # section, paragraph, table
    section_name = Column(String(255))  # Which section this chunk belongs to

    # Token info
    token_count = Column(Integer)
    start_char = Column(Integer)
    end_char = Column(Integer)

    # Embedding
    model_name = Column(String(100), nullable=False)
    dense_vector = Column(Vector(1024))
    sparse_vector = Column(JSONB)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    paper = relationship("Paper", back_populates="chunks")


class ExtractedReference(Base):
    """References extracted from papers."""

    __tablename__ = "extracted_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True)

    # Reference info
    reference_text = Column(Text, nullable=False)
    title = Column(Text)
    authors = Column(ARRAY(String))
    year = Column(Integer)
    venue = Column(String(255))

    # Resolved reference
    resolved_paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=True)

    # Context
    context_sentences = Column(ARRAY(Text))  # Sentences citing this reference

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    paper = relationship("Paper", back_populates="references", foreign_keys=[paper_id])

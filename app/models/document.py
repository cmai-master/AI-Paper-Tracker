"""
PDF Processing models - 처리된 문서 데이터
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Text, Integer, DateTime, Float, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProcessedDocument(Base):
    """처리된 문서 메타데이터"""

    __tablename__ = "processed_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    paper_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Processing Info
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processing_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processor_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Quality Metrics
    text_completeness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    section_coverage_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    table_extraction_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reference_validity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Extraction Stats
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    table_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=False)
    image_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=False)
    reference_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=False)
    equation_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=False)

    # Format Info
    pdf_format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # text, scanned, hybrid
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Storage Paths (S3/MinIO)
    full_text_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sections_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tables_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    sections = relationship("DocumentSection", back_populates="document", cascade="all, delete-orphan")
    tables = relationship("ExtractedTable", back_populates="document", cascade="all, delete-orphan")
    images = relationship("ExtractedImage", back_populates="document", cascade="all, delete-orphan")
    references = relationship("ExtractedReference", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="valid_processing_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<ProcessedDocument(id={self.id}, paper_id={self.paper_id}, status='{self.status}')>"


class DocumentSection(Base):
    """섹션별 텍스트"""

    __tablename__ = "document_sections"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("processed_documents.id", ondelete="CASCADE"), nullable=False
    )

    section_type: Mapped[str] = mapped_column(String(50), nullable=False)  # abstract, introduction, etc.
    section_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "2.1", "3.2.1"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    start_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Hierarchy
    parent_section_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_sections.id"), nullable=True
    )
    section_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("ProcessedDocument", back_populates="sections")

    def __repr__(self) -> str:
        return f"<DocumentSection(id={self.id}, type='{self.section_type}', title='{self.section_title}')>"


class ExtractedTable(Base):
    """추출된 테이블"""

    __tablename__ = "extracted_tables"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("processed_documents.id", ondelete="CASCADE"), nullable=False
    )

    table_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Table Data
    data: Mapped[List[List[str]]] = mapped_column(JSONB, nullable=False)  # 2D array
    headers: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)  # First row as headers
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Table Caption
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caption_position: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # above, below

    # Storage
    csv_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # S3 path to CSV
    image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Screenshot

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("ProcessedDocument", back_populates="tables")

    def __repr__(self) -> str:
        return f"<ExtractedTable(id={self.id}, index={self.table_index}, rows={self.row_count})>"


class ExtractedImage(Base):
    """추출된 이미지"""

    __tablename__ = "extracted_images"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("processed_documents.id", ondelete="CASCADE"), nullable=False
    )

    image_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Image Info
    image_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # figure, diagram, photo, chart
    format: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # png, jpg, svg
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Caption & Context
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Surrounding text

    # Storage
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # S3/MinIO path

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("ProcessedDocument", back_populates="images")

    def __repr__(self) -> str:
        return f"<ExtractedImage(id={self.id}, index={self.image_index}, type='{self.image_type}')>"


class ExtractedReference(Base):
    """추출된 참고문헌"""

    __tablename__ = "extracted_references"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("processed_documents.id", ondelete="CASCADE"), nullable=False
    )

    reference_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Parsed Fields
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[Optional[List[dict]]] = mapped_column(JSONB, nullable=True)  # [{"name": "..."}]
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Journal/Conference

    # External IDs
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Link to our database
    linked_paper_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("papers.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("ProcessedDocument", back_populates="references")

    def __repr__(self) -> str:
        return f"<ExtractedReference(id={self.id}, index={self.reference_index}, title='{self.title}')>"

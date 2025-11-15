"""
Paper models - 논문 메타데이터
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Text, Integer, DateTime, ARRAY, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Paper(Base):
    """논문 메타데이터 메인 테이블"""

    __tablename__ = "papers"

    # Primary Key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # External IDs
    arxiv_id: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, index=True, nullable=True
    )
    doi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    semantic_scholar_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Basic Metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authors: Mapped[List[dict]] = mapped_column(JSONB, nullable=False)  # [{"name": "...", "affiliation": "..."}]

    # Publication Info
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Categories & Keywords
    categories: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    primary_category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    keywords: Mapped[List[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    # URLs
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    abstract_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source Tracking
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "arxiv", "semantic_scholar"
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Processing Status
    processing_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, failed

    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name="valid_processing_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, title='{self.title[:50]}...', arxiv_id='{self.arxiv_id}')>"


class IngestionCheckpoint(Base):
    """수집 체크포인트 테이블"""

    __tablename__ = "ingestion_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    last_sync_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    papers_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("source IS NOT NULL", name="source_not_null"),
    )

    def __repr__(self) -> str:
        return f"<IngestionCheckpoint(source='{self.source}', last_sync={self.last_sync_time})>"


class PaperFingerprint(Base):
    """중복 감지 핑거프린트"""

    __tablename__ = "paper_fingerprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )

    # Hashing fields
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    abstract_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    author_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # External ID mapping
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    semantic_scholar_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Tracking
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    def __repr__(self) -> str:
        return f"<PaperFingerprint(paper_id={self.paper_id}, title_hash='{self.title_hash[:8]}...')>"


class IngestionFailure(Base):
    """수집 실패 로그 (Dead Letter Queue)"""

    __tablename__ = "ingestion_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, retrying, failed, resolved
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("retry_count >= 0", name="valid_retry_count"),
    )

    def __repr__(self) -> str:
        return f"<IngestionFailure(source='{self.source}', external_id='{self.external_id}', status='{self.status}')>"

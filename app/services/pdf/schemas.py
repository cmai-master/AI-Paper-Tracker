"""
PDF Processing schemas
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class PDFFormat(str, Enum):
    """PDF format types"""

    TEXT = "text"  # Normal text-based PDF
    SCANNED = "scanned"  # Scanned PDF requiring OCR
    HYBRID = "hybrid"  # Mix of text and scanned pages


class SectionType(str, Enum):
    """Document section types"""

    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHODOLOGY = "methodology"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    APPENDIX = "appendix"
    ACKNOWLEDGMENTS = "acknowledgments"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractedText(BaseModel):
    """Extracted text from PDF"""

    full_text: str
    page_count: int
    word_count: int
    char_count: int


class Section(BaseModel):
    """Document section"""

    section_type: SectionType
    section_title: Optional[str] = None
    section_number: Optional[str] = None
    content: str
    word_count: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    section_order: int = 0


class TableData(BaseModel):
    """Extracted table data"""

    table_index: int
    page_number: Optional[int] = None
    data: List[List[str]]  # 2D array of strings
    headers: Optional[List[str]] = None
    row_count: int
    column_count: int
    caption: Optional[str] = None
    caption_position: Optional[str] = None


class ImageData(BaseModel):
    """Extracted image data"""

    image_index: int
    page_number: Optional[int] = None
    image_type: Optional[str] = None
    format: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    caption: Optional[str] = None
    storage_path: Optional[str] = None


class Reference(BaseModel):
    """Extracted reference"""

    reference_index: int
    raw_text: str
    title: Optional[str] = None
    authors: Optional[List[Dict]] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None


class QualityMetrics(BaseModel):
    """PDF processing quality metrics"""

    text_completeness_score: float = 0.0  # 0-1
    section_coverage_score: float = 0.0  # 0-1
    table_extraction_score: float = 0.0  # 0-1
    reference_validity_score: float = 0.0  # 0-1
    overall_quality_score: float = 0.0  # 0-1


class ProcessedPDF(BaseModel):
    """Complete processed PDF data"""

    paper_id: str
    processing_started_at: datetime
    processing_completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None

    # Extracted Content
    full_text: str
    sections: List[Section] = Field(default_factory=list)
    tables: List[TableData] = Field(default_factory=list)
    images: List[ImageData] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)

    # Stats
    page_count: int
    word_count: int
    table_count: int = 0
    image_count: int = 0
    reference_count: int = 0
    equation_count: int = 0

    # Format
    pdf_format: PDFFormat
    ocr_used: bool = False

    # Quality
    quality_metrics: QualityMetrics

    # Status
    status: ProcessingStatus = ProcessingStatus.COMPLETED
    error_message: Optional[str] = None


class PDFProcessingResult(BaseModel):
    """Result of PDF processing operation"""

    success: bool
    paper_id: str
    document_id: Optional[str] = None
    processing_time_ms: int
    message: str
    error: Optional[str] = None
    quality_score: Optional[float] = None

"""
PDF Processing API Routes
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.paper import Paper
from app.models.document import ProcessedDocument, DocumentSection
from app.services.pdf.processor import PDFProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pdf", tags=["PDF Processing"])


# Schemas
class PDFProcessRequest(BaseModel):
    """Request to process a PDF"""

    paper_id: UUID = Field(..., description="Paper ID to process")
    force_reprocess: bool = Field(False, description="Force reprocessing")


class PDFProcessResponse(BaseModel):
    """Response from PDF processing"""

    success: bool
    paper_id: str
    document_id: Optional[str] = None
    processing_time_ms: int
    quality_score: Optional[float] = None
    message: str
    error: Optional[str] = None


class DocumentSummary(BaseModel):
    """Summary of processed document"""

    id: UUID
    paper_id: UUID
    status: str
    page_count: Optional[int]
    word_count: Optional[int]
    table_count: Optional[int]
    image_count: Optional[int]
    overall_quality_score: Optional[float]
    processing_duration_ms: Optional[int]
    processing_completed_at: Optional[str]

    class Config:
        from_attributes = True


class SectionSummary(BaseModel):
    """Summary of document section"""

    id: UUID
    section_type: str
    section_title: Optional[str]
    word_count: int
    section_order: int

    class Config:
        from_attributes = True


class DocumentDetail(BaseModel):
    """Detailed document information"""

    id: UUID
    paper_id: UUID
    paper_title: str
    arxiv_id: Optional[str]
    status: str
    page_count: Optional[int]
    word_count: Optional[int]
    table_count: Optional[int]
    image_count: Optional[int]
    pdf_format: Optional[str]
    text_completeness_score: Optional[float]
    section_coverage_score: Optional[float]
    table_extraction_score: Optional[float]
    reference_validity_score: Optional[float]
    overall_quality_score: Optional[float]
    sections: List[SectionSummary]


# Routes
@router.post("/process", response_model=PDFProcessResponse)
async def process_pdf(
    request: PDFProcessRequest,
    db: AsyncSession = Depends(get_db),
) -> PDFProcessResponse:
    """
    Process a paper's PDF

    Downloads, parses, segments, and evaluates quality of a paper's PDF.
    Stores structured data in the database.
    """
    logger.info(f"🚀 Processing PDF for paper: {request.paper_id}")

    try:
        # Get paper
        stmt = select(Paper).where(Paper.id == request.paper_id)
        result = await db.execute(stmt)
        paper = result.scalar_one_or_none()

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        if not paper.arxiv_id:
            raise HTTPException(
                status_code=400, detail="Paper has no arXiv ID for PDF download"
            )

        # Update paper status
        paper.processing_status = "processing"
        await db.commit()

        # Process PDF
        processor = PDFProcessor(db)
        result = await processor.process_paper(
            paper_id=request.paper_id,
            arxiv_id=paper.arxiv_id,
            force_reprocess=request.force_reprocess,
        )

        # Update paper status
        if result.success:
            paper.processing_status = "pdf_processed"
        else:
            paper.processing_status = "failed"

        await db.commit()

        return PDFProcessResponse(
            success=result.success,
            paper_id=result.paper_id,
            document_id=result.document_id,
            processing_time_ms=result.processing_time_ms,
            quality_score=result.quality_score,
            message=result.message,
            error=result.error,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PDF processing failed: {e}", exc_info=True)
        # Update paper status
        paper.processing_status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=List[DocumentSummary])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_quality: Optional[float] = Query(None, description="Minimum quality score", ge=0, le=1),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentSummary]:
    """
    List processed documents

    Returns paginated list of processed documents with optional filters.
    """
    stmt = select(ProcessedDocument)

    # Apply filters
    if status:
        stmt = stmt.where(ProcessedDocument.status == status)

    if min_quality is not None:
        stmt = stmt.where(ProcessedDocument.overall_quality_score >= min_quality)

    # Order by processing date (newest first)
    stmt = (
        stmt.order_by(ProcessedDocument.processing_completed_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    documents = result.scalars().all()

    # Convert to summaries
    summaries = []
    for doc in documents:
        summaries.append(
            DocumentSummary(
                id=doc.id,
                paper_id=doc.paper_id,
                status=doc.status,
                page_count=doc.page_count,
                word_count=doc.word_count,
                table_count=doc.table_count,
                image_count=doc.image_count,
                overall_quality_score=doc.overall_quality_score,
                processing_duration_ms=doc.processing_duration_ms,
                processing_completed_at=doc.processing_completed_at.isoformat()
                if doc.processing_completed_at
                else None,
            )
        )

    return summaries


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    """Get detailed information about a processed document"""
    # Get document
    stmt = select(ProcessedDocument).where(ProcessedDocument.id == document_id)
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get paper
    paper_stmt = select(Paper).where(Paper.id == document.paper_id)
    paper_result = await db.execute(paper_stmt)
    paper = paper_result.scalar_one_or_none()

    # Get sections
    sections_stmt = (
        select(DocumentSection)
        .where(DocumentSection.document_id == document_id)
        .order_by(DocumentSection.section_order)
    )
    sections_result = await db.execute(sections_stmt)
    sections = sections_result.scalars().all()

    section_summaries = [
        SectionSummary(
            id=s.id,
            section_type=s.section_type,
            section_title=s.section_title,
            word_count=s.word_count,
            section_order=s.section_order,
        )
        for s in sections
    ]

    return DocumentDetail(
        id=document.id,
        paper_id=document.paper_id,
        paper_title=paper.title if paper else "Unknown",
        arxiv_id=paper.arxiv_id if paper else None,
        status=document.status,
        page_count=document.page_count,
        word_count=document.word_count,
        table_count=document.table_count,
        image_count=document.image_count,
        pdf_format=document.pdf_format,
        text_completeness_score=document.text_completeness_score,
        section_coverage_score=document.section_coverage_score,
        table_extraction_score=document.table_extraction_score,
        reference_validity_score=document.reference_validity_score,
        overall_quality_score=document.overall_quality_score,
        sections=section_summaries,
    )


@router.get("/documents/{document_id}/sections/{section_id}/content")
async def get_section_content(
    document_id: UUID,
    section_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full content of a document section"""
    stmt = select(DocumentSection).where(
        DocumentSection.id == section_id,
        DocumentSection.document_id == document_id,
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    return {
        "id": section.id,
        "document_id": section.document_id,
        "section_type": section.section_type,
        "section_title": section.section_title,
        "content": section.content,
        "word_count": section.word_count,
        "char_count": section.char_count,
        "section_order": section.section_order,
    }

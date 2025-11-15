"""
Data Ingestion API Routes
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.paper import Paper, IngestionCheckpoint
from app.services.ingestion.arxiv_collector import ArxivCollector
from app.services.ingestion.normalizer import PaperNormalizer
from app.services.ingestion.deduplicator import PaperDeduplicator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingestion", tags=["Data Ingestion"])


# Schemas
class IngestionRequest(BaseModel):
    """Request to ingest papers"""

    categories: Optional[List[str]] = Field(
        None, description="arXiv categories to collect (default: all configured)"
    )
    days_back: int = Field(7, description="Days to look back", ge=1, le=365)
    max_papers: int = Field(1000, description="Maximum papers to collect", ge=1, le=10000)


class IngestionResponse(BaseModel):
    """Response from ingestion"""

    success: bool
    papers_collected: int
    papers_saved: int
    papers_duplicates: int
    processing_time_ms: int
    message: str
    errors: Optional[List[str]] = None


class PaperSummary(BaseModel):
    """Summary of a paper"""

    id: UUID
    arxiv_id: Optional[str]
    title: str
    abstract: Optional[str]
    authors: List[str]
    published_at: datetime
    categories: List[str]
    processing_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class IngestionStats(BaseModel):
    """Ingestion statistics"""

    total_papers: int
    papers_pending: int
    papers_processing: int
    papers_completed: int
    papers_failed: int
    last_ingestion: Optional[datetime]
    categories_tracked: List[str]


# Routes
@router.post("/collect", response_model=IngestionResponse)
async def collect_papers(
    request: IngestionRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Collect papers from arXiv

    Fetches recent papers from arXiv, normalizes them, checks for duplicates,
    and saves new papers to the database.
    """
    start_time = datetime.utcnow()
    logger.info(f"🚀 Starting paper collection: {request.dict()}")

    try:
        # 1. Initialize services
        collector = ArxivCollector(categories=request.categories)
        normalizer = PaperNormalizer()
        deduplicator = PaperDeduplicator(db)

        # 2. Calculate date range
        since = datetime.utcnow() - timedelta(days=request.days_back)

        # 3. Collect papers
        raw_papers = collector.collect_since(since, max_results=request.max_papers)
        logger.info(f"📥 Collected {len(raw_papers)} raw papers")

        if not raw_papers:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return IngestionResponse(
                success=True,
                papers_collected=0,
                papers_saved=0,
                papers_duplicates=0,
                processing_time_ms=duration,
                message="No new papers found",
            )

        # 4. Normalize papers
        normalized_papers = [normalizer.normalize(p) for p in raw_papers]

        # 5. Check for duplicates and save
        saved_count = 0
        duplicate_count = 0
        errors = []

        for paper in normalized_papers:
            try:
                # Check if duplicate
                duplicate_id = await deduplicator.find_duplicate(paper)

                if duplicate_id:
                    duplicate_count += 1
                    logger.debug(f"Duplicate paper: {paper.title[:50]}...")
                    continue

                # Save new paper
                db_paper = Paper(
                    arxiv_id=paper.arxiv_id,
                    doi=paper.doi,
                    title=paper.title,
                    abstract=paper.abstract,
                    authors=paper.authors,
                    published_at=paper.published_at,
                    updated_at=paper.updated_at,
                    categories=paper.categories,
                    pdf_url=paper.pdf_url,
                    comment=paper.comment,
                    journal_ref=paper.journal_ref,
                    primary_category=paper.primary_category,
                    processing_status="pending",
                )
                db.add(db_paper)
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving paper: {e}")
                errors.append(f"Failed to save '{paper.title[:50]}...': {str(e)}")

        # 6. Update checkpoint
        checkpoint = IngestionCheckpoint(
            source="arxiv",
            categories=request.categories or collector.CATEGORIES,
            last_fetched_at=datetime.utcnow(),
            papers_fetched=len(raw_papers),
            papers_saved=saved_count,
        )
        db.add(checkpoint)

        await db.commit()

        duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"✅ Ingestion completed: {saved_count} saved, "
            f"{duplicate_count} duplicates, {duration}ms"
        )

        return IngestionResponse(
            success=True,
            papers_collected=len(raw_papers),
            papers_saved=saved_count,
            papers_duplicates=duplicate_count,
            processing_time_ms=duration,
            message=f"Successfully ingested {saved_count} new papers",
            errors=errors if errors else None,
        )

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/papers", response_model=List[PaperSummary])
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
) -> List[PaperSummary]:
    """
    List ingested papers

    Returns paginated list of papers with optional filters.
    """
    stmt = select(Paper)

    # Apply filters
    if status:
        stmt = stmt.where(Paper.processing_status == status)

    if category:
        stmt = stmt.where(Paper.categories.contains([category]))

    # Order by published date (newest first)
    stmt = stmt.order_by(Paper.published_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    papers = result.scalars().all()

    # Convert to summaries
    summaries = []
    for paper in papers:
        summaries.append(
            PaperSummary(
                id=paper.id,
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                abstract=paper.abstract,
                authors=[author.get("name", "") for author in paper.authors],
                published_at=paper.published_at,
                categories=paper.categories,
                processing_status=paper.processing_status,
                created_at=paper.created_at,
            )
        )

    return summaries


@router.get("/papers/{paper_id}", response_model=PaperSummary)
async def get_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PaperSummary:
    """Get a specific paper by ID"""
    stmt = select(Paper).where(Paper.id == paper_id)
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return PaperSummary(
        id=paper.id,
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        abstract=paper.abstract,
        authors=[author.get("name", "") for author in paper.authors],
        published_at=paper.published_at,
        categories=paper.categories,
        processing_status=paper.processing_status,
        created_at=paper.created_at,
    )


@router.get("/stats", response_model=IngestionStats)
async def get_ingestion_stats(
    db: AsyncSession = Depends(get_db),
) -> IngestionStats:
    """Get ingestion statistics"""
    # Count papers by status
    total_papers = await db.scalar(select(func.count(Paper.id)))

    pending = await db.scalar(
        select(func.count(Paper.id)).where(Paper.processing_status == "pending")
    )

    processing = await db.scalar(
        select(func.count(Paper.id)).where(Paper.processing_status == "processing")
    )

    completed = await db.scalar(
        select(func.count(Paper.id)).where(Paper.processing_status == "completed")
    )

    failed = await db.scalar(
        select(func.count(Paper.id)).where(Paper.processing_status == "failed")
    )

    # Get last checkpoint
    checkpoint_stmt = (
        select(IngestionCheckpoint)
        .order_by(IngestionCheckpoint.created_at.desc())
        .limit(1)
    )
    result = await db.execute(checkpoint_stmt)
    last_checkpoint = result.scalar_one_or_none()

    # Get unique categories
    categories_result = await db.execute(select(func.unnest(Paper.categories)).distinct())
    categories = [row[0] for row in categories_result.all()]

    return IngestionStats(
        total_papers=total_papers or 0,
        papers_pending=pending or 0,
        papers_processing=processing or 0,
        papers_completed=completed or 0,
        papers_failed=failed or 0,
        last_ingestion=last_checkpoint.created_at if last_checkpoint else None,
        categories_tracked=sorted(categories) if categories else [],
    )

"""Paper API routes"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.paper import PaperCreate, PaperResponse
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.paper import Paper

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    paper_data: PaperCreate,
    db: AsyncSession = Depends(get_db),
) -> Paper:
    """
    Create a new paper entry.

    - **arxiv_id**: arXiv ID (must be unique)
    - **title**: Paper title
    - **abstract**: Paper abstract
    - **authors**: List of authors
    - **categories**: List of arXiv categories
    """
    # Check if paper already exists
    stmt = select(Paper).where(Paper.arxiv_id == paper_data.arxiv_id)
    result = await db.execute(stmt)
    existing_paper = result.scalar_one_or_none()

    if existing_paper:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paper with arXiv ID {paper_data.arxiv_id} already exists",
        )

    # Create new paper
    new_paper = Paper(
        arxiv_id=paper_data.arxiv_id,
        title=paper_data.title,
        abstract=paper_data.abstract,
        authors=paper_data.authors,
        categories=paper_data.categories,
        published_date=paper_data.published_date,
        updated_date=paper_data.updated_date,
        doi=paper_data.doi,
        pdf_url=paper_data.pdf_url,
    )

    db.add(new_paper)
    await db.commit()
    await db.refresh(new_paper)

    logger.info("Paper created", paper_id=new_paper.id, arxiv_id=new_paper.arxiv_id)

    return new_paper


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
) -> Paper:
    """
    Get a paper by ID.

    - **paper_id**: Paper ID
    """
    stmt = select(Paper).where(Paper.id == paper_id)
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found",
        )

    return paper


@router.get("/arxiv/{arxiv_id}", response_model=PaperResponse)
async def get_paper_by_arxiv_id(
    arxiv_id: str,
    db: AsyncSession = Depends(get_db),
) -> Paper:
    """
    Get a paper by arXiv ID.

    - **arxiv_id**: arXiv ID (e.g., "2301.12345")
    """
    stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
    result = await db.execute(stmt)
    paper = result.scalar_one_or_none()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper with arXiv ID {arxiv_id} not found",
        )

    return paper


@router.get("/", response_model=List[PaperResponse])
async def list_papers(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    db: AsyncSession = Depends(get_db),
) -> List[Paper]:
    """
    List papers with pagination and optional category filter.

    - **skip**: Number of papers to skip
    - **limit**: Maximum number of papers to return
    - **category**: Optional category filter (e.g., "cs.AI")
    """
    stmt = select(Paper).order_by(desc(Paper.published_date))

    if category:
        # Filter by category (using JSON contains)
        stmt = stmt.where(Paper.categories.contains([category]))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    papers = result.scalars().all()

    return list(papers)


@router.get("/stats/count")
async def get_paper_count(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get total paper count and count by processing status.
    """
    # Total count
    total_stmt = select(func.count(Paper.id))
    total_result = await db.execute(total_stmt)
    total_count = total_result.scalar()

    # Processed count
    processed_stmt = select(func.count(Paper.id)).where(Paper.is_processed == True)
    processed_result = await db.execute(processed_stmt)
    processed_count = processed_result.scalar()

    return {
        "total_papers": total_count,
        "processed_papers": processed_count,
        "unprocessed_papers": total_count - processed_count,
    }

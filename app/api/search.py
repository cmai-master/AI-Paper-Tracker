"""
Vector Search API Routes
"""

import logging
from typing import List, Optional, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.embedding.search import VectorSearchService
from app.services.embedding.schemas import SearchQuery, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


# Schemas
class SearchRequest(BaseModel):
    """Search request"""

    query: str = Field(..., description="Search query text", min_length=1)
    search_type: Literal["dense", "sparse", "hybrid"] = Field(
        "hybrid", description="Type of search"
    )
    top_k: int = Field(10, description="Number of results", ge=1, le=100)
    min_score: Optional[float] = Field(
        None, description="Minimum similarity score", ge=0.0, le=1.0
    )
    filter_section_types: Optional[List[str]] = Field(
        None, description="Filter by section types"
    )
    filter_paper_ids: Optional[List[UUID]] = Field(
        None, description="Filter by paper IDs"
    )


# Routes
@router.post("/papers", response_model=SearchResponse)
async def search_papers(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Search papers by title and abstract

    Performs semantic search across all paper embeddings.
    Returns papers ranked by similarity to the query.

    Search types:
    - dense: Dense vector search (semantic similarity)
    - sparse: Sparse vector search (lexical matching)
    - hybrid: Combines both with Reciprocal Rank Fusion
    """
    try:
        logger.info(f"🔍 Searching papers: '{request.query[:50]}...'")

        search_service = VectorSearchService(db)

        # Create search query
        search_query = SearchQuery(
            query=request.query,
            search_type=request.search_type,
            top_k=request.top_k,
            min_score=request.min_score,
            filter_paper_ids=request.filter_paper_ids,
        )

        # Perform search
        results = await search_service.search_papers(search_query)

        logger.info(
            f"✅ Found {results.total_results} papers in {results.search_time_ms}ms"
        )

        return results

    except Exception as e:
        logger.error(f"❌ Paper search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chunks", response_model=SearchResponse)
async def search_chunks(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Search document chunks

    Performs fine-grained semantic search across all text chunks.
    Returns specific passages ranked by similarity.

    Use this for:
    - Finding specific information within papers
    - Detailed content retrieval
    - Context extraction for QA
    """
    try:
        logger.info(f"🔍 Searching chunks: '{request.query[:50]}...'")

        search_service = VectorSearchService(db)

        search_query = SearchQuery(
            query=request.query,
            search_type=request.search_type,
            top_k=request.top_k,
            min_score=request.min_score,
            filter_section_types=request.filter_section_types,
            filter_paper_ids=request.filter_paper_ids,
        )

        results = await search_service.search_chunks(search_query)

        logger.info(
            f"✅ Found {results.total_results} chunks in {results.search_time_ms}ms"
        )

        return results

    except Exception as e:
        logger.error(f"❌ Chunk search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sections", response_model=SearchResponse)
async def search_sections(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Search document sections

    Searches across document sections (abstract, intro, methods, etc.).
    Returns entire sections ranked by similarity.

    Use this for:
    - Section-level comparison
    - Finding papers with similar methodologies
    - Comparing experimental setups
    """
    try:
        logger.info(f"🔍 Searching sections: '{request.query[:50]}...'")

        search_service = VectorSearchService(db)

        search_query = SearchQuery(
            query=request.query,
            search_type=request.search_type,
            top_k=request.top_k,
            min_score=request.min_score,
            filter_section_types=request.filter_section_types,
            filter_paper_ids=request.filter_paper_ids,
        )

        results = await search_service.search_sections(search_query)

        logger.info(
            f"✅ Found {results.total_results} sections in {results.search_time_ms}ms"
        )

        return results

    except Exception as e:
        logger.error(f"❌ Section search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def search_all(
    q: str = Query(..., description="Search query", min_length=1),
    type: Literal["dense", "sparse", "hybrid"] = Query("hybrid", description="Search type"),
    limit: int = Query(10, description="Number of results", ge=1, le=100),
    min_score: Optional[float] = Query(None, description="Minimum score", ge=0, le=1),
    section_type: Optional[str] = Query(None, description="Filter by section type"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Universal search endpoint

    Searches across papers, chunks, and sections simultaneously.
    Returns combined results for comprehensive discovery.
    """
    try:
        logger.info(f"🔍 Universal search: '{q[:50]}...'")

        search_service = VectorSearchService(db)

        search_query = SearchQuery(
            query=q,
            search_type=type,
            top_k=limit,
            min_score=min_score,
            filter_section_types=[section_type] if section_type else None,
        )

        # Search all types
        papers = await search_service.search_papers(search_query)
        chunks = await search_service.search_chunks(search_query)
        sections = await search_service.search_sections(search_query)

        return {
            "query": q,
            "papers": {
                "total": papers.total_results,
                "results": papers.results,
                "search_time_ms": papers.search_time_ms,
            },
            "chunks": {
                "total": chunks.total_results,
                "results": chunks.results,
                "search_time_ms": chunks.search_time_ms,
            },
            "sections": {
                "total": sections.total_results,
                "results": sections.results,
                "search_time_ms": sections.search_time_ms,
            },
        }

    except Exception as e:
        logger.error(f"❌ Universal search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar/papers/{paper_id}", response_model=SearchResponse)
async def find_similar_papers(
    paper_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    min_score: Optional[float] = Query(0.5, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """
    Find papers similar to a given paper

    Uses the paper's title and abstract to find related papers.
    """
    from app.models.paper import Paper
    from sqlalchemy import select

    try:
        # Get the source paper
        stmt = select(Paper).where(Paper.id == paper_id)
        result = await db.execute(stmt)
        paper = result.scalar_one_or_none()

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Create search query from paper's title and abstract
        query_text = f"{paper.title}\n\n{paper.abstract or ''}"

        search_service = VectorSearchService(db)

        search_query = SearchQuery(
            query=query_text,
            search_type="hybrid",
            top_k=limit + 1,  # +1 because source paper will be in results
            min_score=min_score,
        )

        results = await search_service.search_papers(search_query)

        # Filter out the source paper itself
        filtered_results = [r for r in results.results if r.paper_id != paper_id]
        results.results = filtered_results[:limit]
        results.total_results = len(filtered_results)

        logger.info(
            f"✅ Found {results.total_results} similar papers for {paper_id}"
        )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Similar papers search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

"""
Embedding Generation API Routes
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.paper import Paper
from app.models.document import ProcessedDocument
from app.services.embedding.processor import EmbeddingProcessor
from app.services.embedding.schemas import EmbeddingStats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/embedding", tags=["Embeddings"])


# Schemas
class EmbeddingRequest(BaseModel):
    """Request to generate embeddings"""

    paper_id: UUID = Field(..., description="Paper ID to generate embeddings for")
    force_reprocess: bool = Field(False, description="Force reprocessing")
    chunking_strategy: str = Field("semantic", description="Chunking strategy")
    chunk_size: int = Field(512, description="Chunk size in tokens", ge=128, le=2048)
    chunk_overlap: int = Field(50, description="Chunk overlap in tokens", ge=0, le=512)


class EmbeddingResponse(BaseModel):
    """Response from embedding generation"""

    success: bool
    paper_id: str
    paper_embedding_id: Optional[str] = None
    chunk_count: int = 0
    section_count: int = 0
    processing_time_ms: int = 0
    message: str
    error: Optional[str] = None


# Routes
@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embeddings(
    request: EmbeddingRequest,
    db: AsyncSession = Depends(get_db),
) -> EmbeddingResponse:
    """
    Generate embeddings for a paper

    Creates paper-level, chunk-level, and section-level embeddings
    for semantic search.

    Prerequisites:
    - Paper must be ingested
    - PDF must be processed
    """
    logger.info(f"🚀 Generating embeddings for paper: {request.paper_id}")

    try:
        # Verify paper exists
        stmt = select(Paper).where(Paper.id == request.paper_id)
        result = await db.execute(stmt)
        paper = result.scalar_one_or_none()

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Verify PDF is processed
        doc_stmt = select(ProcessedDocument).where(
            ProcessedDocument.paper_id == request.paper_id
        )
        doc_result = await db.execute(doc_stmt)
        document = doc_result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=400,
                detail="PDF not processed yet. Process PDF first using /api/v1/pdf/process",
            )

        if document.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"PDF processing not completed (status: {document.status})",
            )

        # Update paper status
        paper.processing_status = "embedding"
        await db.commit()

        # Generate embeddings
        processor = EmbeddingProcessor(
            db=db,
            chunking_strategy=request.chunking_strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

        result = await processor.process_paper(
            paper_id=request.paper_id,
            force_reprocess=request.force_reprocess,
        )

        # Update paper status
        if result["success"]:
            paper.processing_status = "completed"
        else:
            paper.processing_status = "failed"

        await db.commit()

        return EmbeddingResponse(
            success=result["success"],
            paper_id=result["paper_id"],
            paper_embedding_id=result.get("paper_embedding_id"),
            chunk_count=result.get("chunk_count", 0),
            section_count=result.get("section_count", 0),
            processing_time_ms=result.get("processing_time_ms", 0),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}", exc_info=True)
        # Update paper status
        paper.processing_status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/generate")
async def batch_generate_embeddings(
    paper_ids: list[UUID] = Field(..., description="List of paper IDs"),
    force_reprocess: bool = Field(False, description="Force reprocessing"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate embeddings for multiple papers

    Processes embeddings in batch for improved efficiency.
    """
    logger.info(f"🚀 Batch generating embeddings for {len(paper_ids)} papers")

    results = {
        "total": len(paper_ids),
        "successful": 0,
        "failed": 0,
        "details": [],
    }

    processor = EmbeddingProcessor(db=db)

    for paper_id in paper_ids:
        try:
            result = await processor.process_paper(
                paper_id=paper_id,
                force_reprocess=force_reprocess,
            )

            if result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "paper_id": str(paper_id),
                "success": result["success"],
                "message": result.get("message", ""),
                "error": result.get("error"),
            })

        except Exception as e:
            logger.error(f"Error processing paper {paper_id}: {e}")
            results["failed"] += 1
            results["details"].append({
                "paper_id": str(paper_id),
                "success": False,
                "error": str(e),
            })

    return results


@router.get("/stats", response_model=EmbeddingStats)
async def get_embedding_stats(
    db: AsyncSession = Depends(get_db),
) -> EmbeddingStats:
    """
    Get embedding statistics

    Returns counts of embeddings and processing statistics.
    """
    processor = EmbeddingProcessor(db=db)
    stats = await processor.get_embedding_stats()
    return stats


@router.delete("/papers/{paper_id}")
async def delete_paper_embeddings(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete all embeddings for a paper

    Removes paper, chunk, and section embeddings.
    Useful for reprocessing or cleanup.
    """
    from app.models.embedding import PaperEmbedding, ChunkEmbedding, SectionEmbedding

    try:
        # Delete paper embedding
        paper_emb_stmt = select(PaperEmbedding).where(PaperEmbedding.paper_id == paper_id)
        paper_emb_result = await db.execute(paper_emb_stmt)
        paper_emb = paper_emb_result.scalar_one_or_none()
        if paper_emb:
            await db.delete(paper_emb)

        # Delete chunk embeddings
        chunk_stmt = select(ChunkEmbedding).where(ChunkEmbedding.paper_id == paper_id)
        chunk_result = await db.execute(chunk_stmt)
        chunks = chunk_result.scalars().all()
        for chunk in chunks:
            await db.delete(chunk)

        # Delete section embeddings
        section_stmt = select(SectionEmbedding).where(SectionEmbedding.paper_id == paper_id)
        section_result = await db.execute(section_stmt)
        sections = section_result.scalars().all()
        for section in sections:
            await db.delete(section)

        await db.commit()

        return {
            "success": True,
            "paper_id": str(paper_id),
            "deleted": {
                "paper_embedding": 1 if paper_emb else 0,
                "chunk_embeddings": len(chunks),
                "section_embeddings": len(sections),
            },
            "message": "Embeddings deleted successfully",
        }

    except Exception as e:
        logger.error(f"❌ Failed to delete embeddings: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

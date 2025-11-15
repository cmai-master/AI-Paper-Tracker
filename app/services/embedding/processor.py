"""
Embedding Processor - Complete embedding pipeline
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.models.document import ProcessedDocument, DocumentSection
from app.models.embedding import (
    PaperEmbedding,
    ChunkEmbedding,
    SectionEmbedding,
)
from app.services.embedding.embedder import get_embedder
from app.services.embedding.chunker import create_chunker
from app.services.embedding.schemas import (
    ChunkingStrategy,
    PaperEmbeddingData,
    ChunkEmbeddingData,
    SectionEmbeddingData,
    EmbeddingStats,
)

logger = logging.getLogger(__name__)


class EmbeddingProcessor:
    """
    Complete embedding processing pipeline

    Pipeline:
    1. Generate paper-level embedding (title + abstract)
    2. Chunk document text
    3. Generate chunk embeddings
    4. Generate section embeddings
    """

    def __init__(
        self,
        db: AsyncSession,
        chunking_strategy: str = "semantic",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        """
        Initialize embedding processor

        Args:
            db: Database session
            chunking_strategy: Strategy for text chunking
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
        """
        self.db = db
        self.embedder = get_embedder()
        self.chunker = create_chunker(
            strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    async def process_paper(
        self,
        paper_id: UUID,
        force_reprocess: bool = False,
    ) -> dict:
        """
        Process all embeddings for a paper

        Args:
            paper_id: Paper UUID
            force_reprocess: Force reprocessing even if exists

        Returns:
            Processing result
        """
        start_time = datetime.utcnow()
        logger.info(f"🚀 Processing embeddings for paper: {paper_id}")

        try:
            # 1. Check if already processed
            if not force_reprocess:
                existing = await self._get_paper_embedding(paper_id)
                if existing:
                    logger.info(f"✓ Paper embeddings already exist: {paper_id}")
                    return {
                        "success": True,
                        "paper_id": str(paper_id),
                        "message": "Already processed",
                        "reprocessed": False,
                    }

            # 2. Get paper and document
            paper = await self._get_paper(paper_id)
            if not paper:
                return {
                    "success": False,
                    "paper_id": str(paper_id),
                    "error": "Paper not found",
                }

            document = await self._get_processed_document(paper_id)
            if not document:
                return {
                    "success": False,
                    "paper_id": str(paper_id),
                    "error": "Processed document not found - run PDF processing first",
                }

            # 3. Generate paper-level embedding
            paper_emb_id = await self._process_paper_embedding(paper)

            # 4. Get sections
            sections = await self._get_sections(document.id)

            # 5. Generate chunk embeddings
            chunk_count = await self._process_chunk_embeddings(
                paper_id, document.id, sections
            )

            # 6. Generate section embeddings
            section_count = await self._process_section_embeddings(
                paper_id, document.id, sections
            )

            await self.db.commit()

            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.info(
                f"✅ Embedding processing completed in {duration}ms | "
                f"Chunks: {chunk_count}, Sections: {section_count}"
            )

            return {
                "success": True,
                "paper_id": str(paper_id),
                "paper_embedding_id": str(paper_emb_id),
                "chunk_count": chunk_count,
                "section_count": section_count,
                "processing_time_ms": duration,
                "message": "Processing completed successfully",
            }

        except Exception as e:
            logger.error(f"❌ Embedding processing failed: {e}", exc_info=True)
            await self.db.rollback()

            return {
                "success": False,
                "paper_id": str(paper_id),
                "error": str(e),
            }

    async def _process_paper_embedding(self, paper: Paper) -> UUID:
        """Generate and save paper-level embedding"""
        logger.info(f"📄 Generating paper embedding: {paper.title[:50]}...")

        # Combine title and abstract
        source_text = f"{paper.title}\n\n{paper.abstract or ''}"

        # Generate text hash for deduplication
        text_hash = hashlib.sha256(source_text.encode()).hexdigest()

        # Check if already exists
        stmt = select(PaperEmbedding).where(
            PaperEmbedding.paper_id == paper.id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        # Generate embedding
        embedding_result = self.embedder.embed_document(source_text)

        if existing:
            # Update existing
            existing.dense_vector = embedding_result.dense_vector
            existing.sparse_vector = embedding_result.sparse_vector
            existing.source_text = source_text
            existing.text_hash = text_hash
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing.id
        else:
            # Create new
            paper_embedding = PaperEmbedding(
                paper_id=paper.id,
                dense_vector=embedding_result.dense_vector,
                sparse_vector=embedding_result.sparse_vector,
                source_text=source_text,
                text_hash=text_hash,
            )
            self.db.add(paper_embedding)
            await self.db.commit()
            await self.db.refresh(paper_embedding)
            return paper_embedding.id

    async def _process_chunk_embeddings(
        self, paper_id: UUID, document_id: UUID, sections: List[DocumentSection]
    ) -> int:
        """Generate and save chunk embeddings"""
        logger.info(f"✂️ Chunking and embedding document sections...")

        # Delete existing chunks for reprocessing
        stmt = select(ChunkEmbedding).where(ChunkEmbedding.document_id == document_id)
        result = await self.db.execute(stmt)
        existing_chunks = result.scalars().all()
        for chunk in existing_chunks:
            await self.db.delete(chunk)

        # Chunk all sections
        section_dicts = [
            {
                "content": s.content,
                "section_type": s.section_type,
                "section_title": s.section_title,
            }
            for s in sections
        ]

        chunks = self.chunker.chunk_document_sections(section_dicts)

        if not chunks:
            logger.warning("No chunks created from document")
            return 0

        # Generate embeddings in batches
        chunk_texts = [c.text for c in chunks]
        batch_result = self.embedder.embed_batch(chunk_texts, show_progress=True)

        # Save chunk embeddings
        for i, (chunk, dense_vec) in enumerate(
            zip(chunks, batch_result.dense_vectors)
        ):
            sparse_vec = None
            if batch_result.sparse_vectors:
                sparse_vec = batch_result.sparse_vectors[i]

            chunk_embedding = ChunkEmbedding(
                document_id=document_id,
                paper_id=paper_id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.text,
                chunk_size=chunk.chunk_size,
                word_count=chunk.word_count,
                section_type=chunk.section_type,
                section_title=chunk.section_title,
                page_number=chunk.page_number,
                dense_vector=dense_vec,
                sparse_vector=sparse_vec,
            )
            self.db.add(chunk_embedding)

        await self.db.flush()

        logger.info(f"✅ Created {len(chunks)} chunk embeddings")
        return len(chunks)

    async def _process_section_embeddings(
        self, paper_id: UUID, document_id: UUID, sections: List[DocumentSection]
    ) -> int:
        """Generate and save section embeddings"""
        logger.info(f"📑 Generating section embeddings...")

        if not sections:
            return 0

        # Delete existing section embeddings
        stmt = select(SectionEmbedding).where(
            SectionEmbedding.document_id == document_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().all()
        for emb in existing:
            await self.db.delete(emb)

        # Generate embeddings in batch
        section_texts = [s.content for s in sections]
        batch_result = self.embedder.embed_batch(section_texts, show_progress=False)

        # Save section embeddings
        for i, (section, dense_vec) in enumerate(
            zip(sections, batch_result.dense_vectors)
        ):
            sparse_vec = None
            if batch_result.sparse_vectors:
                sparse_vec = batch_result.sparse_vectors[i]

            section_embedding = SectionEmbedding(
                section_id=section.id,
                document_id=document_id,
                paper_id=paper_id,
                section_type=section.section_type,
                section_title=section.section_title,
                section_text=section.content,
                word_count=section.word_count,
                dense_vector=dense_vec,
                sparse_vector=sparse_vec,
            )
            self.db.add(section_embedding)

        await self.db.flush()

        logger.info(f"✅ Created {len(sections)} section embeddings")
        return len(sections)

    async def _get_paper(self, paper_id: UUID) -> Optional[Paper]:
        """Get paper by ID"""
        stmt = select(Paper).where(Paper.id == paper_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_processed_document(self, paper_id: UUID) -> Optional[ProcessedDocument]:
        """Get processed document"""
        stmt = select(ProcessedDocument).where(ProcessedDocument.paper_id == paper_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_sections(self, document_id: UUID) -> List[DocumentSection]:
        """Get document sections"""
        stmt = (
            select(DocumentSection)
            .where(DocumentSection.document_id == document_id)
            .order_by(DocumentSection.section_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_paper_embedding(self, paper_id: UUID) -> Optional[PaperEmbedding]:
        """Get existing paper embedding"""
        stmt = select(PaperEmbedding).where(PaperEmbedding.paper_id == paper_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_embedding_stats(self) -> EmbeddingStats:
        """Get embedding statistics"""
        # Count embeddings
        paper_count = await self.db.scalar(select(func.count(PaperEmbedding.id)))
        chunk_count = await self.db.scalar(select(func.count(ChunkEmbedding.id)))
        section_count = await self.db.scalar(select(func.count(SectionEmbedding.id)))

        # Calculate average chunks per paper
        avg_chunks = 0.0
        if paper_count > 0:
            avg_chunks = chunk_count / paper_count

        return EmbeddingStats(
            total_paper_embeddings=paper_count or 0,
            total_chunk_embeddings=chunk_count or 0,
            total_section_embeddings=section_count or 0,
            total_entity_embeddings=0,  # TODO: Implement entity embeddings
            avg_chunks_per_paper=avg_chunks,
            last_updated=datetime.utcnow(),
        )


# Example usage
if __name__ == "__main__":
    import asyncio
    from app.core.database import AsyncSessionLocal

    logging.basicConfig(level=logging.INFO)

    async def main():
        async with AsyncSessionLocal() as db:
            processor = EmbeddingProcessor(db)

            # Example paper ID (replace with actual UUID)
            from uuid import uuid4

            paper_id = uuid4()

            # Process embeddings
            result = await processor.process_paper(paper_id)

            print(f"\n{'='*60}")
            print(f"Embedding Processing Result:")
            print(f"{'='*60}")
            for key, value in result.items():
                print(f"{key}: {value}")

            # Get stats
            stats = await processor.get_embedding_stats()
            print(f"\n{'='*60}")
            print(f"Embedding Statistics:")
            print(f"{'='*60}")
            print(f"Paper embeddings: {stats.total_paper_embeddings}")
            print(f"Chunk embeddings: {stats.total_chunk_embeddings}")
            print(f"Section embeddings: {stats.total_section_embeddings}")
            print(f"Avg chunks/paper: {stats.avg_chunks_per_paper:.1f}")

    asyncio.run(main())

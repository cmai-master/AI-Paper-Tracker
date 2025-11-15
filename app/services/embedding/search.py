"""
Vector Search Service - Semantic search using pgvector
"""

import logging
import time
from typing import List, Optional, Dict, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from app.models.embedding import (
    PaperEmbedding,
    ChunkEmbedding,
    SectionEmbedding,
    EntityEmbedding,
)
from app.models.paper import Paper
from app.services.embedding.schemas import SearchQuery, SearchResult, SearchResponse
from app.services.embedding.embedder import get_embedder

logger = logging.getLogger(__name__)


class VectorSearchService:
    """
    Vector search service using pgvector

    Supports:
    - Dense vector search (cosine similarity)
    - Sparse vector search (lexical matching)
    - Hybrid search (RRF - Reciprocal Rank Fusion)
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize search service

        Args:
            db: Database session
        """
        self.db = db
        self.embedder = get_embedder()

    async def search_papers(self, query: SearchQuery) -> SearchResponse:
        """
        Search papers by title/abstract

        Args:
            query: Search query

        Returns:
            SearchResponse with results
        """
        start_time = time.time()

        # Generate query embedding
        query_result = self.embedder.embed_query(query.query)

        # Perform search
        if query.search_type == "dense":
            results = await self._search_dense_papers(
                query_result.dense_vector, query
            )
        elif query.search_type == "sparse":
            results = await self._search_sparse_papers(
                query_result.sparse_vector, query
            )
        else:  # hybrid
            results = await self._search_hybrid_papers(
                query_result.dense_vector, query_result.sparse_vector, query
            )

        search_time = int((time.time() - start_time) * 1000)

        return SearchResponse(
            query=query.query,
            results=results,
            total_results=len(results),
            search_type=query.search_type,
            search_time_ms=search_time,
        )

    async def search_chunks(self, query: SearchQuery) -> SearchResponse:
        """
        Search document chunks

        Args:
            query: Search query

        Returns:
            SearchResponse with results
        """
        start_time = time.time()

        # Generate query embedding
        query_result = self.embedder.embed_query(query.query)

        # Perform search
        if query.search_type == "dense":
            results = await self._search_dense_chunks(
                query_result.dense_vector, query
            )
        elif query.search_type == "sparse":
            results = await self._search_sparse_chunks(
                query_result.sparse_vector, query
            )
        else:  # hybrid
            results = await self._search_hybrid_chunks(
                query_result.dense_vector, query_result.sparse_vector, query
            )

        search_time = int((time.time() - start_time) * 1000)

        return SearchResponse(
            query=query.query,
            results=results,
            total_results=len(results),
            search_type=query.search_type,
            search_time_ms=search_time,
        )

    async def search_sections(self, query: SearchQuery) -> SearchResponse:
        """
        Search document sections

        Args:
            query: Search query

        Returns:
            SearchResponse with results
        """
        start_time = time.time()

        # Generate query embedding
        query_result = self.embedder.embed_query(query.query)

        # Perform search
        if query.search_type == "dense":
            results = await self._search_dense_sections(
                query_result.dense_vector, query
            )
        elif query.search_type == "sparse":
            results = await self._search_sparse_sections(
                query_result.sparse_vector, query
            )
        else:  # hybrid
            results = await self._search_hybrid_sections(
                query_result.dense_vector, query_result.sparse_vector, query
            )

        search_time = int((time.time() - start_time) * 1000)

        return SearchResponse(
            query=query.query,
            results=results,
            total_results=len(results),
            search_type=query.search_type,
            search_time_ms=search_time,
        )

    # Dense search implementations
    async def _search_dense_papers(
        self, query_vector: List[float], query: SearchQuery
    ) -> List[SearchResult]:
        """Dense vector search on papers"""
        # Build query
        stmt = (
            select(
                PaperEmbedding,
                Paper,
                PaperEmbedding.dense_vector.cosine_distance(query_vector).label(
                    "distance"
                ),
            )
            .join(Paper, PaperEmbedding.paper_id == Paper.id)
            .where(PaperEmbedding.dense_vector.isnot(None))
        )

        # Apply filters
        if query.filter_paper_ids:
            stmt = stmt.where(PaperEmbedding.paper_id.in_(query.filter_paper_ids))

        # Order by similarity (lower distance = higher similarity)
        stmt = stmt.order_by("distance").limit(query.top_k)

        result = await self.db.execute(stmt)
        rows = result.all()

        # Convert to SearchResult
        results = []
        for embedding, paper, distance in rows:
            # Convert distance to similarity (cosine similarity = 1 - cosine distance)
            similarity = 1.0 - distance

            # Apply min_score filter
            if query.min_score and similarity < query.min_score:
                continue

            results.append(
                SearchResult(
                    id=embedding.id,
                    paper_id=paper.id,
                    text=embedding.source_text,
                    score=similarity,
                    section_type=None,
                    section_title=None,
                    chunk_index=None,
                    paper_title=paper.title,
                    paper_authors=[
                        author.get("name") for author in paper.authors
                    ],
                    arxiv_id=paper.arxiv_id,
                )
            )

        return results

    async def _search_dense_chunks(
        self, query_vector: List[float], query: SearchQuery
    ) -> List[SearchResult]:
        """Dense vector search on chunks"""
        stmt = (
            select(
                ChunkEmbedding,
                Paper,
                ChunkEmbedding.dense_vector.cosine_distance(query_vector).label(
                    "distance"
                ),
            )
            .join(Paper, ChunkEmbedding.paper_id == Paper.id)
            .where(ChunkEmbedding.dense_vector.isnot(None))
        )

        # Apply filters
        if query.filter_paper_ids:
            stmt = stmt.where(ChunkEmbedding.paper_id.in_(query.filter_paper_ids))

        if query.filter_section_types:
            stmt = stmt.where(
                ChunkEmbedding.section_type.in_(query.filter_section_types)
            )

        stmt = stmt.order_by("distance").limit(query.top_k)

        result = await self.db.execute(stmt)
        rows = result.all()

        results = []
        for embedding, paper, distance in rows:
            similarity = 1.0 - distance

            if query.min_score and similarity < query.min_score:
                continue

            results.append(
                SearchResult(
                    id=embedding.id,
                    paper_id=paper.id,
                    text=embedding.chunk_text,
                    score=similarity,
                    section_type=embedding.section_type,
                    section_title=embedding.section_title,
                    chunk_index=embedding.chunk_index,
                    paper_title=paper.title,
                    paper_authors=[
                        author.get("name") for author in paper.authors
                    ],
                    arxiv_id=paper.arxiv_id,
                )
            )

        return results

    async def _search_dense_sections(
        self, query_vector: List[float], query: SearchQuery
    ) -> List[SearchResult]:
        """Dense vector search on sections"""
        stmt = (
            select(
                SectionEmbedding,
                Paper,
                SectionEmbedding.dense_vector.cosine_distance(query_vector).label(
                    "distance"
                ),
            )
            .join(Paper, SectionEmbedding.paper_id == Paper.id)
            .where(SectionEmbedding.dense_vector.isnot(None))
        )

        # Apply filters
        if query.filter_paper_ids:
            stmt = stmt.where(SectionEmbedding.paper_id.in_(query.filter_paper_ids))

        if query.filter_section_types:
            stmt = stmt.where(
                SectionEmbedding.section_type.in_(query.filter_section_types)
            )

        stmt = stmt.order_by("distance").limit(query.top_k)

        result = await self.db.execute(stmt)
        rows = result.all()

        results = []
        for embedding, paper, distance in rows:
            similarity = 1.0 - distance

            if query.min_score and similarity < query.min_score:
                continue

            results.append(
                SearchResult(
                    id=embedding.id,
                    paper_id=paper.id,
                    text=embedding.section_text[:500],  # Truncate for display
                    score=similarity,
                    section_type=embedding.section_type,
                    section_title=embedding.section_title,
                    chunk_index=None,
                    paper_title=paper.title,
                    paper_authors=[
                        author.get("name") for author in paper.authors
                    ],
                    arxiv_id=paper.arxiv_id,
                )
            )

        return results

    # Sparse search implementations (placeholder - requires custom indexing)
    async def _search_sparse_papers(
        self, query_sparse: Dict, query: SearchQuery
    ) -> List[SearchResult]:
        """Sparse (lexical) search on papers - uses PostgreSQL full-text search"""
        # For now, use simple text search as placeholder
        # TODO: Implement proper sparse vector search with custom scoring
        logger.warning("Sparse search not fully implemented, using dense fallback")
        return []

    async def _search_sparse_chunks(
        self, query_sparse: Dict, query: SearchQuery
    ) -> List[SearchResult]:
        """Sparse search on chunks"""
        logger.warning("Sparse search not fully implemented, using dense fallback")
        return []

    async def _search_sparse_sections(
        self, query_sparse: Dict, query: SearchQuery
    ) -> List[SearchResult]:
        """Sparse search on sections"""
        logger.warning("Sparse search not fully implemented, using dense fallback")
        return []

    # Hybrid search implementations (RRF - Reciprocal Rank Fusion)
    async def _search_hybrid_papers(
        self, query_dense: List[float], query_sparse: Dict, query: SearchQuery
    ) -> List[SearchResult]:
        """Hybrid search combining dense and sparse"""
        # Get dense results
        dense_results = await self._search_dense_papers(query_dense, query)

        # Get sparse results (if implemented)
        # sparse_results = await self._search_sparse_papers(query_sparse, query)

        # For now, just return dense results
        # TODO: Implement RRF fusion
        return dense_results

    async def _search_hybrid_chunks(
        self, query_dense: List[float], query_sparse: Dict, query: SearchQuery
    ) -> List[SearchResult]:
        """Hybrid chunk search"""
        dense_results = await self._search_dense_chunks(query_dense, query)
        return dense_results

    async def _search_hybrid_sections(
        self, query_dense: List[float], query_sparse: Dict, query: SearchQuery
    ) -> List[SearchResult]:
        """Hybrid section search"""
        dense_results = await self._search_dense_sections(query_dense, query)
        return dense_results

    def _reciprocal_rank_fusion(
        self, dense_results: List[SearchResult], sparse_results: List[SearchResult], k: int = 60
    ) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion algorithm

        RRF(d) = Σ 1 / (k + rank(d))

        Args:
            dense_results: Results from dense search
            sparse_results: Results from sparse search
            k: RRF constant (default 60)

        Returns:
            Fused results
        """
        # Build score map
        scores = {}

        # Add dense scores
        for rank, result in enumerate(dense_results, start=1):
            scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank)

        # Add sparse scores
        for rank, result in enumerate(sparse_results, start=1):
            scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank)

        # Combine all results
        all_results = {r.id: r for r in dense_results + sparse_results}

        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Build final results with RRF scores
        fused_results = []
        for result_id in sorted_ids:
            result = all_results[result_id]
            result.score = scores[result_id]  # Replace with RRF score
            fused_results.append(result)

        return fused_results


# Example usage
if __name__ == "__main__":
    import asyncio
    from app.core.database import AsyncSessionLocal

    logging.basicConfig(level=logging.INFO)

    async def main():
        async with AsyncSessionLocal() as db:
            search_service = VectorSearchService(db)

            # Example search
            query = SearchQuery(
                query="What are transformer models in deep learning?",
                search_type="hybrid",
                top_k=5,
            )

            print(f"\n{'='*60}")
            print(f"Search Query: {query.query}")
            print(f"{'='*60}\n")

            # Search papers
            paper_results = await search_service.search_papers(query)
            print(f"Paper Results: {paper_results.total_results}")
            for i, result in enumerate(paper_results.results, 1):
                print(f"{i}. [{result.score:.4f}] {result.paper_title}")
                print(f"   arXiv: {result.arxiv_id}")
                print(f"   Text: {result.text[:200]}...")
                print()

            # Search chunks
            chunk_results = await search_service.search_chunks(query)
            print(f"\nChunk Results: {chunk_results.total_results}")
            for i, result in enumerate(chunk_results.results[:3], 1):
                print(f"{i}. [{result.score:.4f}] {result.paper_title}")
                print(f"   Section: {result.section_type}")
                print(f"   Text: {result.text[:200]}...")
                print()

    asyncio.run(main())

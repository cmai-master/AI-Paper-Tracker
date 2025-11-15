"""Main embedding service for generating and storing embeddings."""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
import structlog

from paperpulse.models.paper import Paper, ProcessedDocument, PaperEmbedding, ChunkEmbedding
from paperpulse.services.embedding.embedding_generator import HybridEmbeddingGenerator
from paperpulse.services.embedding.text_chunker import TextChunker, SemanticChunker

logger = structlog.get_logger()


class EmbeddingService:
    """Service for generating and managing embeddings."""

    def __init__(self, db: Session, model: str = "bge"):
        self.db = db
        self.generator = HybridEmbeddingGenerator(prefer_model=model)
        self.chunker = SemanticChunker(target_chunk_size=512)
        self.model = model

    async def generate_paper_embeddings(self, paper_id: str) -> Dict[str, int]:
        """
        Generate embeddings for a paper.

        Creates:
        - Full text embedding
        - Abstract embedding
        - Section embeddings
        - Chunk embeddings

        Args:
            paper_id: Paper UUID

        Returns:
            Dictionary with counts of generated embeddings
        """
        stats = {
            "paper_embeddings": 0,
            "chunk_embeddings": 0,
        }

        # Get paper and processed document
        paper = self.db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            logger.error("paper_not_found", paper_id=paper_id)
            return stats

        doc = (
            self.db.query(ProcessedDocument)
            .filter(ProcessedDocument.paper_id == paper_id)
            .first()
        )

        if not doc or not doc.full_text:
            logger.error("no_processed_document", paper_id=paper_id)
            return stats

        logger.info("generating_embeddings", paper_id=paper_id)

        try:
            # 1. Generate paper-level embeddings
            await self._generate_paper_level_embeddings(paper, doc)
            stats["paper_embeddings"] += 1

            # 2. Generate chunk-level embeddings
            chunk_count = await self._generate_chunk_embeddings(paper, doc)
            stats["chunk_embeddings"] = chunk_count

            logger.info(
                "embedding_generation_completed",
                paper_id=paper_id,
                stats=stats,
            )

        except Exception as e:
            logger.error(
                "embedding_generation_failed",
                paper_id=paper_id,
                error=str(e),
                exc_info=True,
            )
            raise

        return stats

    async def _generate_paper_level_embeddings(
        self, paper: Paper, doc: ProcessedDocument
    ):
        """Generate document-level embeddings."""

        # Delete existing paper embeddings
        self.db.query(PaperEmbedding).filter(
            PaperEmbedding.paper_id == paper.id
        ).delete()

        # Generate embeddings for different content types
        embeddings_to_create = []

        # 1. Abstract embedding
        if paper.abstract:
            abstract_emb = await self.generator.generate(paper.abstract, self.model)
            embeddings_to_create.append(
                {
                    "type": "abstract",
                    "embedding": abstract_emb,
                }
            )

        # 2. Full text embedding (first 8k chars to avoid token limits)
        if doc.full_text:
            full_text_sample = doc.full_text[:8000]
            full_text_emb = await self.generator.generate(full_text_sample, self.model)
            embeddings_to_create.append(
                {
                    "type": "full_text",
                    "embedding": full_text_emb,
                }
            )

        # 3. Section embeddings (if available)
        if doc.sections:
            # Introduction
            if "introduction" in doc.sections:
                intro_emb = await self.generator.generate(
                    doc.sections["introduction"][:4000], self.model
                )
                embeddings_to_create.append(
                    {
                        "type": "introduction",
                        "embedding": intro_emb,
                    }
                )

            # Conclusion
            if "conclusion" in doc.sections:
                conclusion_emb = await self.generator.generate(
                    doc.sections["conclusion"][:4000], self.model
                )
                embeddings_to_create.append(
                    {
                        "type": "conclusion",
                        "embedding": conclusion_emb,
                    }
                )

        # Save to database
        for emb_data in embeddings_to_create:
            paper_emb = PaperEmbedding(
                paper_id=paper.id,
                embedding_type=emb_data["type"],
                model_name=self.model,
                dense_vector=emb_data["embedding"].tolist(),
            )
            self.db.add(paper_emb)

        self.db.commit()

        logger.info(
            "paper_level_embeddings_created",
            paper_id=str(paper.id),
            count=len(embeddings_to_create),
        )

    async def _generate_chunk_embeddings(
        self, paper: Paper, doc: ProcessedDocument
    ) -> int:
        """Generate chunk-level embeddings."""

        # Delete existing chunk embeddings
        self.db.query(ChunkEmbedding).filter(
            ChunkEmbedding.paper_id == paper.id
        ).delete()

        # Chunk the text
        chunks = []

        if doc.sections:
            # Chunk by sections
            chunks = self.chunker.chunk_by_sections(doc.sections)
        elif doc.full_text:
            # Chunk full text
            chunks = self.chunker.chunk(doc.full_text)

        if not chunks:
            return 0

        # Generate embeddings for all chunks
        chunk_texts = [chunk["chunk_text"] for chunk in chunks]
        embeddings = await self.generator.generate_batch(chunk_texts, self.model)

        # Save to database
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_emb = ChunkEmbedding(
                paper_id=paper.id,
                chunk_index=i,
                chunk_text=chunk["chunk_text"],
                chunk_type="semantic",
                section_name=chunk.get("section"),
                token_count=chunk.get("token_count"),
                start_char=0,  # TODO: track actual positions
                end_char=chunk.get("char_count", 0),
                model_name=self.model,
                dense_vector=embedding.tolist(),
            )
            self.db.add(chunk_emb)

        self.db.commit()

        logger.info(
            "chunk_embeddings_created",
            paper_id=str(paper.id),
            chunk_count=len(chunks),
        )

        return len(chunks)

    async def search_similar_papers(
        self,
        query: str,
        top_k: int = 10,
        embedding_type: str = "abstract",
    ) -> List[Dict]:
        """
        Search for similar papers using vector similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            embedding_type: Type of embedding to search ("abstract", "full_text", etc.)

        Returns:
            List of similar papers with scores
        """
        # Generate query embedding
        query_embedding = await self.generator.generate(query, self.model)

        # Search using pgvector
        # Convert numpy array to list for SQL
        query_vector = query_embedding.tolist()

        # Use pgvector's cosine distance operator (<=>)
        sql = text("""
            SELECT
                p.id,
                p.title,
                p.abstract,
                p.authors,
                p.published_at,
                p.arxiv_id,
                p.citation_count,
                (pe.dense_vector <=> :query_vector::vector) as distance,
                1 - (pe.dense_vector <=> :query_vector::vector) as similarity
            FROM papers p
            JOIN paper_embeddings pe ON p.id = pe.paper_id
            WHERE pe.embedding_type = :embedding_type
                AND pe.model_name = :model
            ORDER BY pe.dense_vector <=> :query_vector::vector
            LIMIT :top_k
        """)

        result = self.db.execute(
            sql,
            {
                "query_vector": query_vector,
                "embedding_type": embedding_type,
                "model": self.model,
                "top_k": top_k,
            },
        ).fetchall()

        papers = []
        for row in result:
            papers.append(
                {
                    "id": str(row[0]),
                    "title": row[1],
                    "abstract": row[2],
                    "authors": row[3],
                    "published_at": row[4],
                    "arxiv_id": row[5],
                    "citation_count": row[6],
                    "distance": float(row[7]),
                    "similarity": float(row[8]),
                }
            )

        logger.info(
            "similarity_search_completed",
            query_length=len(query),
            results=len(papers),
        )

        return papers

    async def search_similar_chunks(
        self, query: str, top_k: int = 20, section: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for similar chunks using vector similarity.

        Args:
            query: Search query
            top_k: Number of results
            section: Optional section filter

        Returns:
            List of similar chunks with paper info
        """
        # Generate query embedding
        query_embedding = await self.generator.generate(query, self.model)
        query_vector = query_embedding.tolist()

        # Build SQL
        if section:
            sql = text("""
                SELECT
                    p.id as paper_id,
                    p.title,
                    p.arxiv_id,
                    ce.chunk_text,
                    ce.section_name,
                    ce.chunk_index,
                    1 - (ce.dense_vector <=> :query_vector::vector) as similarity
                FROM chunk_embeddings ce
                JOIN papers p ON ce.paper_id = p.id
                WHERE ce.model_name = :model
                    AND ce.section_name = :section
                ORDER BY ce.dense_vector <=> :query_vector::vector
                LIMIT :top_k
            """)
            params = {
                "query_vector": query_vector,
                "model": self.model,
                "section": section,
                "top_k": top_k,
            }
        else:
            sql = text("""
                SELECT
                    p.id as paper_id,
                    p.title,
                    p.arxiv_id,
                    ce.chunk_text,
                    ce.section_name,
                    ce.chunk_index,
                    1 - (ce.dense_vector <=> :query_vector::vector) as similarity
                FROM chunk_embeddings ce
                JOIN papers p ON ce.paper_id = p.id
                WHERE ce.model_name = :model
                ORDER BY ce.dense_vector <=> :query_vector::vector
                LIMIT :top_k
            """)
            params = {
                "query_vector": query_vector,
                "model": self.model,
                "top_k": top_k,
            }

        result = self.db.execute(sql, params).fetchall()

        chunks = []
        for row in result:
            chunks.append(
                {
                    "paper_id": str(row[0]),
                    "paper_title": row[1],
                    "arxiv_id": row[2],
                    "chunk_text": row[3],
                    "section_name": row[4],
                    "chunk_index": row[5],
                    "similarity": float(row[6]),
                }
            )

        return chunks

"""Main ingestion service orchestrating the collection pipeline."""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import asyncio
import structlog

from paperpulse.models.paper import Paper
from paperpulse.services.ingestion.arxiv_collector import ArxivCollector
from paperpulse.services.ingestion.semantic_scholar_collector import SemanticScholarCollector
from paperpulse.services.ingestion.normalizer import PaperNormalizer
from paperpulse.services.ingestion.deduplicator import PaperDeduplicator

logger = structlog.get_logger()


class IngestionService:
    """Main service for paper ingestion pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.arxiv_collector = ArxivCollector()
        self.semantic_scholar_collector = SemanticScholarCollector()
        self.normalizer = PaperNormalizer()
        self.deduplicator = PaperDeduplicator(db)

    async def ingest_recent_papers(
        self, days_back: int = 7, enrich_with_semantic_scholar: bool = True
    ) -> Dict[str, int]:
        """
        Ingest recent AI/ML papers from arXiv.

        Args:
            days_back: How many days back to collect
            enrich_with_semantic_scholar: Whether to enrich with Semantic Scholar data

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(
            "ingestion_started",
            days_back=days_back,
            enrich=enrich_with_semantic_scholar,
        )

        stats = {
            "collected": 0,
            "normalized": 0,
            "new": 0,
            "duplicates": 0,
            "stored": 0,
            "enriched": 0,
            "errors": 0,
        }

        try:
            # 1. Collect from arXiv
            raw_papers = self.arxiv_collector.collect_recent_ai_papers(
                days_back=days_back
            )
            stats["collected"] = len(raw_papers)

            logger.info("arxiv_collection_completed", count=len(raw_papers))

            # 2. Normalize papers
            normalized_papers = []
            for paper in raw_papers:
                normalized = self.normalizer.normalize(paper, source="arxiv")
                if normalized:
                    normalized_papers.append(normalized)

            stats["normalized"] = len(normalized_papers)

            logger.info("normalization_completed", count=len(normalized_papers))

            # 3. Deduplicate
            new_papers, duplicates = self.deduplicator.deduplicate_batch(
                normalized_papers
            )
            stats["new"] = len(new_papers)
            stats["duplicates"] = len(duplicates)

            logger.info(
                "deduplication_completed",
                new=len(new_papers),
                duplicates=len(duplicates),
            )

            # 4. Handle duplicates (merge data)
            for paper_data, existing in duplicates:
                try:
                    self.deduplicator.merge_duplicate(existing, paper_data)
                except Exception as e:
                    logger.error(
                        "duplicate_merge_failed",
                        error=str(e),
                        title=paper_data.get("title", "")[:50],
                    )
                    stats["errors"] += 1

            # 5. Store new papers
            for paper_data in new_papers:
                try:
                    paper = self._create_paper(paper_data)
                    self.db.add(paper)
                    stats["stored"] += 1
                except Exception as e:
                    logger.error(
                        "paper_storage_failed",
                        error=str(e),
                        title=paper_data.get("title", "")[:50],
                    )
                    stats["errors"] += 1

            self.db.commit()

            logger.info("papers_stored", count=stats["stored"])

            # 6. Enrich with Semantic Scholar (optional)
            if enrich_with_semantic_scholar:
                stats["enriched"] = await self._enrich_papers(new_papers)

            logger.info("ingestion_completed", stats=stats)

        except Exception as e:
            logger.error("ingestion_failed", error=str(e), exc_info=True)
            self.db.rollback()
            raise

        return stats

    async def ingest_by_query(
        self, query: str, max_results: int = 100, source: str = "arxiv"
    ) -> Dict[str, int]:
        """
        Ingest papers by custom query.

        Args:
            query: Search query
            max_results: Maximum papers to collect
            source: Data source ("arxiv" or "semantic_scholar")

        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            "collected": 0,
            "normalized": 0,
            "new": 0,
            "duplicates": 0,
            "stored": 0,
            "errors": 0,
        }

        try:
            # Collect papers
            if source == "arxiv":
                raw_papers = self.arxiv_collector.collect_papers(
                    query=query, max_results=max_results
                )
            elif source == "semantic_scholar":
                raw_papers = await self.semantic_scholar_collector.search_papers(
                    query=query, limit=max_results
                )
            else:
                raise ValueError(f"Unknown source: {source}")

            stats["collected"] = len(raw_papers)

            # Normalize
            normalized_papers = []
            for paper in raw_papers:
                normalized = self.normalizer.normalize(paper, source=source)
                if normalized:
                    normalized_papers.append(normalized)

            stats["normalized"] = len(normalized_papers)

            # Deduplicate and store
            new_papers, duplicates = self.deduplicator.deduplicate_batch(
                normalized_papers
            )
            stats["new"] = len(new_papers)
            stats["duplicates"] = len(duplicates)

            # Merge duplicates
            for paper_data, existing in duplicates:
                try:
                    self.deduplicator.merge_duplicate(existing, paper_data)
                except Exception as e:
                    logger.error("duplicate_merge_failed", error=str(e))
                    stats["errors"] += 1

            # Store new papers
            for paper_data in new_papers:
                try:
                    paper = self._create_paper(paper_data)
                    self.db.add(paper)
                    stats["stored"] += 1
                except Exception as e:
                    logger.error("paper_storage_failed", error=str(e))
                    stats["errors"] += 1

            self.db.commit()

            logger.info("query_ingestion_completed", stats=stats)

        except Exception as e:
            logger.error("query_ingestion_failed", error=str(e), exc_info=True)
            self.db.rollback()
            raise

        return stats

    async def _enrich_papers(self, papers: List[Dict]) -> int:
        """
        Enrich papers with Semantic Scholar data.

        Args:
            papers: List of normalized paper dictionaries

        Returns:
            Number of papers enriched
        """
        enriched_count = 0

        for paper_data in papers:
            arxiv_id = paper_data.get("arxiv_id")
            if not arxiv_id:
                continue

            try:
                # Get Semantic Scholar data
                s2_data = await self.semantic_scholar_collector.enrich_arxiv_paper(
                    arxiv_id
                )

                if s2_data:
                    # Find the paper in database
                    paper = (
                        self.db.query(Paper)
                        .filter(Paper.arxiv_id == arxiv_id)
                        .first()
                    )

                    if paper:
                        # Update with S2 data
                        paper.semantic_scholar_id = s2_data.get("semantic_scholar_id")
                        paper.citation_count = s2_data.get("citation_count", 0)
                        paper.references_count = s2_data.get("references_count", 0)
                        paper.semantic_scholar_data = s2_data.get(
                            "semantic_scholar_data"
                        )

                        enriched_count += 1

                # Rate limiting
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(
                    "enrichment_failed",
                    arxiv_id=arxiv_id,
                    error=str(e),
                )

        self.db.commit()

        logger.info("enrichment_completed", enriched=enriched_count)

        return enriched_count

    def _create_paper(self, paper_data: Dict) -> Paper:
        """
        Create Paper model instance from normalized data.

        Args:
            paper_data: Normalized paper dictionary

        Returns:
            Paper model instance
        """
        return Paper(
            arxiv_id=paper_data.get("arxiv_id"),
            doi=paper_data.get("doi"),
            semantic_scholar_id=paper_data.get("semantic_scholar_id"),
            title=paper_data.get("title"),
            abstract=paper_data.get("abstract"),
            authors=paper_data.get("authors"),
            published_at=paper_data.get("published_at"),
            updated_at=paper_data.get("updated_at"),
            categories=paper_data.get("categories"),
            primary_category=paper_data.get("primary_category"),
            journal=paper_data.get("journal"),
            venue=paper_data.get("venue"),
            pdf_url=paper_data.get("pdf_url"),
            source_url=paper_data.get("source_url"),
            citation_count=paper_data.get("citation_count", 0),
            references_count=paper_data.get("references_count", 0),
            semantic_scholar_data=paper_data.get("semantic_scholar_data"),
            processing_status=paper_data.get("processing_status", "pending"),
        )

    async def update_paper_metrics(self, paper_id: str) -> Optional[Paper]:
        """
        Update citation counts and other metrics for a paper.

        Args:
            paper_id: Paper UUID

        Returns:
            Updated Paper or None if not found
        """
        paper = self.db.query(Paper).filter(Paper.id == paper_id).first()

        if not paper:
            return None

        try:
            # Try to get updated data from Semantic Scholar
            if paper.semantic_scholar_id:
                s2_data = await self.semantic_scholar_collector.get_paper_by_id(
                    paper.semantic_scholar_id
                )

                if s2_data:
                    paper.citation_count = s2_data.get("citation_count", 0)
                    paper.references_count = s2_data.get("references_count", 0)
                    paper.semantic_scholar_data = s2_data.get("semantic_scholar_data")

            elif paper.arxiv_id:
                s2_data = await self.semantic_scholar_collector.enrich_arxiv_paper(
                    paper.arxiv_id
                )

                if s2_data:
                    paper.semantic_scholar_id = s2_data.get("semantic_scholar_id")
                    paper.citation_count = s2_data.get("citation_count", 0)
                    paper.references_count = s2_data.get("references_count", 0)
                    paper.semantic_scholar_data = s2_data.get("semantic_scholar_data")

            self.db.commit()

            logger.info(
                "paper_metrics_updated",
                paper_id=str(paper.id),
                citations=paper.citation_count,
            )

        except Exception as e:
            logger.error(
                "metrics_update_failed",
                paper_id=str(paper.id),
                error=str(e),
            )
            self.db.rollback()

        return paper

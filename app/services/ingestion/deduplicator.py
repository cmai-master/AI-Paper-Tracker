"""
Paper deduplication logic
"""

import logging
from typing import Optional
from uuid import UUID
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper, PaperFingerprint
from app.services.ingestion.schemas import NormalizedPaper

logger = logging.getLogger(__name__)


class PaperDeduplicator:
    """논문 중복 감지 및 제거"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_duplicate(self, paper: NormalizedPaper) -> Optional[UUID]:
        """
        Find duplicate paper in database

        Args:
            paper: Normalized paper to check

        Returns:
            UUID of existing paper if duplicate found, None otherwise
        """
        # Strategy 1: arXiv ID lookup
        if paper.arxiv_id:
            stmt = select(PaperFingerprint).where(
                PaperFingerprint.arxiv_id == paper.arxiv_id
            )
            result = await self.db.execute(stmt)
            fingerprint = result.scalar_one_or_none()

            if fingerprint:
                logger.info(f"✓ Duplicate found via arXiv ID: {paper.arxiv_id}")
                return fingerprint.paper_id

        # Strategy 2: DOI lookup
        if paper.doi:
            stmt = select(PaperFingerprint).where(PaperFingerprint.doi == paper.doi)
            result = await self.db.execute(stmt)
            fingerprint = result.scalar_one_or_none()

            if fingerprint:
                logger.info(f"✓ Duplicate found via DOI: {paper.doi}")
                return fingerprint.paper_id

        # Strategy 3: Title + Author hash lookup
        stmt = select(PaperFingerprint).where(
            PaperFingerprint.title_hash == paper.title_hash,
            PaperFingerprint.author_hash == paper.author_hash,
        )
        result = await self.db.execute(stmt)
        fingerprint = result.scalar_one_or_none()

        if fingerprint:
            logger.info(f"✓ Duplicate found via title+author hash: {paper.title[:50]}")
            return fingerprint.paper_id

        # Strategy 4: Fuzzy title matching (for papers from last 30 days)
        similar = await self._fuzzy_title_search(paper.title)
        if similar:
            logger.info(f"✓ Potential duplicate found via fuzzy match: {paper.title[:50]}")
            return similar.paper_id

        logger.debug(f"✗ No duplicate found for: {paper.title[:50]}")
        return None

    async def _fuzzy_title_search(
        self, title: str, threshold: float = 0.9
    ) -> Optional[PaperFingerprint]:
        """
        Fuzzy search for similar titles

        Args:
            title: Paper title to search
            threshold: Similarity threshold (0-1)

        Returns:
            PaperFingerprint if similar paper found, None otherwise
        """
        # Get recent papers (last 1000) for fuzzy matching
        stmt = (
            select(Paper)
            .order_by(Paper.published_at.desc())
            .limit(1000)
        )
        result = await self.db.execute(stmt)
        recent_papers = result.scalars().all()

        title_lower = title.lower()

        for existing_paper in recent_papers:
            similarity = SequenceMatcher(
                None, title_lower, existing_paper.title.lower()
            ).ratio()

            if similarity >= threshold:
                # Get fingerprint for this paper
                stmt = select(PaperFingerprint).where(
                    PaperFingerprint.paper_id == existing_paper.id
                )
                result = await self.db.execute(stmt)
                return result.scalar_one_or_none()

        return None

    async def merge_metadata(self, existing_id: UUID, new_paper: NormalizedPaper) -> Paper:
        """
        Merge metadata from new paper into existing paper

        Args:
            existing_id: ID of existing paper
            new_paper: New paper data to merge

        Returns:
            Updated paper
        """
        stmt = select(Paper).where(Paper.id == existing_id)
        result = await self.db.execute(stmt)
        existing = result.scalar_one()

        # Update fields if new data is more complete
        if new_paper.doi and not existing.doi:
            existing.doi = new_paper.doi
            logger.debug(f"Updated DOI for paper {existing_id}")

        if new_paper.semantic_scholar_id and not existing.semantic_scholar_id:
            existing.semantic_scholar_id = new_paper.semantic_scholar_id
            logger.debug(f"Updated Semantic Scholar ID for paper {existing_id}")

        # Merge categories (union)
        if new_paper.categories:
            existing.categories = list(set(existing.categories + new_paper.categories))
            logger.debug(f"Merged categories for paper {existing_id}")

        # Update timestamp
        from datetime import datetime
        existing.last_updated = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(existing)

        logger.info(f"✅ Merged metadata for duplicate paper {existing_id}")
        return existing

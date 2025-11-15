"""
Paper data normalizer
"""

import re
import logging
from typing import Optional

from app.services.ingestion.schemas import RawPaper, NormalizedPaper, DataSource

logger = logging.getLogger(__name__)


class PaperNormalizer:
    """논문 데이터 정규화"""

    def normalize(self, raw_paper: RawPaper) -> NormalizedPaper:
        """
        Normalize raw paper data

        Args:
            raw_paper: Raw paper from external source

        Returns:
            Normalized paper
        """
        # Extract IDs based on source
        arxiv_id = None
        doi = None
        semantic_scholar_id = None

        if raw_paper.source == DataSource.ARXIV:
            arxiv_id = raw_paper.external_id
            # Extract DOI from raw metadata if available
            if "doi" in raw_paper.raw_metadata and raw_paper.raw_metadata["doi"]:
                doi = raw_paper.raw_metadata["doi"]

        elif raw_paper.source == DataSource.SEMANTIC_SCHOLAR:
            semantic_scholar_id = raw_paper.external_id
            # Extract arXiv ID from external IDs if available
            external_ids = raw_paper.raw_metadata.get("externalIds", {})
            if "arXiv" in external_ids:
                arxiv_id = external_ids["arXiv"]
            if "DOI" in external_ids:
                doi = external_ids["DOI"]

        # Normalize title and abstract
        title = self._normalize_title(raw_paper.title)
        abstract = self._normalize_abstract(raw_paper.abstract)

        # Extract primary category
        primary_category = raw_paper.categories[0] if raw_paper.categories else None

        # Create normalized paper
        normalized = NormalizedPaper(
            arxiv_id=arxiv_id,
            doi=doi,
            semantic_scholar_id=semantic_scholar_id,
            title=title,
            abstract=abstract,
            authors=raw_paper.authors,
            published_at=raw_paper.published_at,
            updated_at=raw_paper.updated_at,
            categories=raw_paper.categories,
            primary_category=primary_category,
            pdf_url=raw_paper.pdf_url,
            data_source=raw_paper.source,
        )

        # Compute hashes for deduplication
        normalized.compute_hashes()

        logger.debug(f"Normalized paper: {title[:50]}...")

        return normalized

    def _normalize_title(self, title: str) -> str:
        """
        Normalize paper title

        Args:
            title: Raw title

        Returns:
            Normalized title
        """
        # Remove extra whitespace
        title = re.sub(r"\s+", " ", title)

        # Remove leading/trailing whitespace
        title = title.strip()

        # Remove LaTeX commands (basic cleanup)
        title = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", title)
        title = re.sub(r"[{}]", "", title)

        return title

    def _normalize_abstract(self, abstract: Optional[str]) -> Optional[str]:
        """
        Normalize abstract

        Args:
            abstract: Raw abstract

        Returns:
            Normalized abstract or None
        """
        if not abstract:
            return None

        # Remove extra whitespace
        abstract = re.sub(r"\s+", " ", abstract)

        # Remove leading/trailing whitespace
        abstract = abstract.strip()

        # Remove newlines
        abstract = abstract.replace("\n", " ")

        return abstract

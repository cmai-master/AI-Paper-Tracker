"""Paper deduplication service."""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
import structlog

from paperpulse.models.paper import Paper
from paperpulse.services.ingestion.normalizer import PaperMerger

logger = structlog.get_logger()


class PaperDeduplicator:
    """Detect and handle duplicate papers."""

    def __init__(self, db: Session):
        self.db = db
        self.merger = PaperMerger()

    def find_duplicates(self, paper: Dict) -> List[Paper]:
        """
        Find existing papers that match the given paper.

        Matching criteria (in order of priority):
        1. Exact arXiv ID match
        2. Exact DOI match
        3. Exact Semantic Scholar ID match
        4. Title hash + author hash match

        Args:
            paper: Normalized paper dictionary

        Returns:
            List of matching Paper records
        """
        matches = []

        # 1. Check arXiv ID
        if paper.get("arxiv_id"):
            arxiv_match = (
                self.db.query(Paper)
                .filter(Paper.arxiv_id == paper["arxiv_id"])
                .first()
            )
            if arxiv_match:
                matches.append(arxiv_match)
                return matches  # arXiv ID is unique, return immediately

        # 2. Check DOI
        if paper.get("doi"):
            doi_match = (
                self.db.query(Paper)
                .filter(Paper.doi == paper["doi"])
                .first()
            )
            if doi_match:
                matches.append(doi_match)
                return matches  # DOI is unique, return immediately

        # 3. Check Semantic Scholar ID
        if paper.get("semantic_scholar_id"):
            s2_match = (
                self.db.query(Paper)
                .filter(Paper.semantic_scholar_id == paper["semantic_scholar_id"])
                .first()
            )
            if s2_match:
                matches.append(s2_match)
                return matches  # S2 ID is unique, return immediately

        # 4. Fuzzy matching by title (for papers without external IDs)
        # This is a fallback for edge cases
        if paper.get("title"):
            # Clean title for comparison
            title = paper["title"].lower().strip()

            similar_papers = (
                self.db.query(Paper)
                .filter(Paper.title.ilike(f"%{title}%"))
                .limit(10)
                .all()
            )

            # Calculate similarity scores
            for candidate in similar_papers:
                if self._is_likely_duplicate(paper, candidate):
                    matches.append(candidate)

        return matches

    def deduplicate_batch(
        self, papers: List[Dict]
    ) -> Tuple[List[Dict], List[Tuple[Dict, Paper]]]:
        """
        Deduplicate a batch of papers.

        Args:
            papers: List of normalized paper dictionaries

        Returns:
            Tuple of (new_papers, duplicate_papers_with_matches)
        """
        new_papers = []
        duplicates = []

        for paper in papers:
            matches = self.find_duplicates(paper)

            if matches:
                # Found duplicate - return with match
                duplicates.append((paper, matches[0]))
                logger.info(
                    "duplicate_detected",
                    title=paper.get("title", "")[:50],
                    arxiv_id=paper.get("arxiv_id"),
                    matched_id=str(matches[0].id),
                )
            else:
                # New paper
                new_papers.append(paper)

        logger.info(
            "deduplication_completed",
            total_papers=len(papers),
            new_papers=len(new_papers),
            duplicates=len(duplicates),
        )

        return new_papers, duplicates

    def merge_duplicate(
        self, existing: Paper, new_data: Dict
    ) -> Paper:
        """
        Merge new data into existing paper record.

        Args:
            existing: Existing Paper database record
            new_data: New normalized paper data

        Returns:
            Updated Paper record
        """
        # Convert existing paper to dict
        existing_dict = {
            "arxiv_id": existing.arxiv_id,
            "doi": existing.doi,
            "semantic_scholar_id": existing.semantic_scholar_id,
            "title": existing.title,
            "abstract": existing.abstract,
            "authors": existing.authors,
            "published_at": existing.published_at,
            "updated_at": existing.updated_at,
            "categories": existing.categories,
            "primary_category": existing.primary_category,
            "journal": existing.journal,
            "venue": existing.venue,
            "pdf_url": existing.pdf_url,
            "source_url": existing.source_url,
            "citation_count": existing.citation_count,
            "references_count": existing.references_count,
            "semantic_scholar_data": existing.semantic_scholar_data,
        }

        # Merge with new data
        merged = self.merger.merge([existing_dict, new_data])

        # Update existing record with merged data
        existing.arxiv_id = merged.get("arxiv_id") or existing.arxiv_id
        existing.doi = merged.get("doi") or existing.doi
        existing.semantic_scholar_id = (
            merged.get("semantic_scholar_id") or existing.semantic_scholar_id
        )
        existing.title = merged.get("title") or existing.title
        existing.abstract = merged.get("abstract") or existing.abstract
        existing.authors = merged.get("authors") or existing.authors
        existing.published_at = merged.get("published_at") or existing.published_at
        existing.updated_at = merged.get("updated_at") or existing.updated_at
        existing.categories = merged.get("categories") or existing.categories
        existing.primary_category = (
            merged.get("primary_category") or existing.primary_category
        )
        existing.journal = merged.get("journal") or existing.journal
        existing.venue = merged.get("venue") or existing.venue
        existing.pdf_url = merged.get("pdf_url") or existing.pdf_url
        existing.citation_count = max(
            merged.get("citation_count", 0), existing.citation_count or 0
        )
        existing.references_count = max(
            merged.get("references_count", 0), existing.references_count or 0
        )

        # Merge Semantic Scholar data
        if merged.get("semantic_scholar_data"):
            if existing.semantic_scholar_data:
                existing.semantic_scholar_data.update(
                    merged["semantic_scholar_data"]
                )
            else:
                existing.semantic_scholar_data = merged["semantic_scholar_data"]

        self.db.commit()

        logger.info(
            "paper_merged",
            paper_id=str(existing.id),
            title=existing.title[:50],
        )

        return existing

    def _is_likely_duplicate(self, paper: Dict, candidate: Paper) -> bool:
        """
        Check if paper is likely a duplicate of candidate using fuzzy matching.

        Args:
            paper: Normalized paper dictionary
            candidate: Candidate Paper record from database

        Returns:
            True if likely duplicate, False otherwise
        """
        # Title similarity
        title1 = paper.get("title", "").lower().strip()
        title2 = candidate.title.lower().strip() if candidate.title else ""

        # Simple check: if titles are very similar (Levenshtein distance could be used)
        if self._calculate_similarity(title1, title2) > 0.9:
            # Check if authors overlap
            authors1 = set(a.lower() for a in paper.get("authors", []))
            authors2 = set(a.lower() for a in (candidate.authors or []))

            if authors1 and authors2:
                # Calculate Jaccard similarity
                intersection = len(authors1 & authors2)
                union = len(authors1 | authors2)
                author_similarity = intersection / union if union > 0 else 0

                if author_similarity > 0.5:
                    return True

        return False

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate simple similarity score between two strings.

        Uses a simple character-based similarity metric.
        For production, consider using Levenshtein distance or similar.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0

        # Simple character overlap ratio
        set1 = set(str1.lower())
        set2 = set(str2.lower())

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

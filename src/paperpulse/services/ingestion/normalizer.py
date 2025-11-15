"""Paper metadata normalizer and validator."""

from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import structlog

logger = structlog.get_logger()


class PaperNormalizer:
    """Normalize and validate paper metadata from different sources."""

    def normalize(self, paper: Dict, source: str) -> Optional[Dict]:
        """
        Normalize paper metadata to standard schema.

        Args:
            paper: Raw paper metadata
            source: Data source ("arxiv", "semantic_scholar", etc.)

        Returns:
            Normalized paper dictionary or None if validation fails
        """
        try:
            if source == "arxiv":
                normalized = self._normalize_arxiv(paper)
            elif source == "semantic_scholar":
                normalized = self._normalize_semantic_scholar(paper)
            else:
                logger.warning("unknown_source", source=source)
                return None

            # Validate required fields
            if not self._validate(normalized):
                return None

            # Add fingerprints for deduplication
            normalized["fingerprints"] = self._generate_fingerprints(normalized)

            return normalized

        except Exception as e:
            logger.error(
                "normalization_failed",
                source=source,
                error=str(e),
                exc_info=True,
            )
            return None

    def _normalize_arxiv(self, paper: Dict) -> Dict:
        """Normalize arXiv paper data."""
        return {
            "arxiv_id": paper.get("arxiv_id"),
            "doi": paper.get("doi"),
            "semantic_scholar_id": None,
            "title": self._clean_text(paper.get("title", "")),
            "abstract": self._clean_text(paper.get("abstract", "")),
            "authors": self._normalize_authors(paper.get("authors", [])),
            "published_at": self._normalize_date(paper.get("published_at")),
            "updated_at": self._normalize_date(paper.get("updated_at")),
            "categories": paper.get("categories", []),
            "primary_category": paper.get("primary_category"),
            "journal": paper.get("journal"),
            "venue": None,
            "pdf_url": paper.get("pdf_url"),
            "source_url": paper.get("source_url"),
            "citation_count": 0,  # Not available from arXiv
            "references_count": 0,
            # Additional data
            "comment": paper.get("comment"),
            "data_source": "arxiv",
            "processing_status": "pending",
        }

    def _normalize_semantic_scholar(self, paper: Dict) -> Dict:
        """Normalize Semantic Scholar paper data."""
        return {
            "arxiv_id": paper.get("arxiv_id"),
            "doi": paper.get("doi"),
            "semantic_scholar_id": paper.get("semantic_scholar_id"),
            "title": self._clean_text(paper.get("title", "")),
            "abstract": self._clean_text(paper.get("abstract", "")),
            "authors": self._normalize_authors(paper.get("authors", [])),
            "published_at": self._normalize_date(paper.get("published_at")),
            "updated_at": None,
            "categories": paper.get("s2_fields_of_study", []),
            "primary_category": (
                paper.get("s2_fields_of_study", [None])[0]
                if paper.get("s2_fields_of_study")
                else None
            ),
            "journal": paper.get("journal"),
            "venue": paper.get("venue"),
            "pdf_url": paper.get("pdf_url"),
            "source_url": f"https://www.semanticscholar.org/paper/{paper.get('semantic_scholar_id')}",
            "citation_count": paper.get("citation_count", 0),
            "references_count": paper.get("references_count", 0),
            # Store full Semantic Scholar data
            "semantic_scholar_data": paper.get("semantic_scholar_data"),
            "data_source": "semantic_scholar",
            "processing_status": "pending",
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = " ".join(text.split())

        # Remove trailing/leading whitespace
        text = text.strip()

        return text

    def _normalize_authors(self, authors: List) -> List[str]:
        """
        Normalize author names.

        Args:
            authors: List of author names or dicts

        Returns:
            List of normalized author name strings
        """
        normalized = []

        for author in authors:
            if isinstance(author, str):
                name = author
            elif isinstance(author, dict):
                name = author.get("name", "")
            else:
                continue

            # Clean and normalize name
            name = self._clean_text(name)
            if name:
                normalized.append(name)

        return normalized

    def _normalize_date(self, date) -> Optional[datetime]:
        """
        Normalize date to datetime object.

        Args:
            date: Date string, datetime object, or None

        Returns:
            Normalized datetime or None
        """
        if isinstance(date, datetime):
            return date

        if isinstance(date, str):
            try:
                return datetime.fromisoformat(date.replace("Z", "+00:00"))
            except ValueError:
                logger.warning("invalid_date_format", date=date)
                return None

        return None

    def _validate(self, paper: Dict) -> bool:
        """
        Validate normalized paper has required fields.

        Args:
            paper: Normalized paper dictionary

        Returns:
            True if valid, False otherwise
        """
        # Required fields
        required = ["title", "authors", "published_at"]

        for field in required:
            if not paper.get(field):
                logger.warning(
                    "validation_failed_missing_field",
                    field=field,
                    title=paper.get("title", "")[:50],
                )
                return False

        # At least one external ID
        if not any(
            [
                paper.get("arxiv_id"),
                paper.get("doi"),
                paper.get("semantic_scholar_id"),
            ]
        ):
            logger.warning(
                "validation_failed_no_external_id",
                title=paper.get("title", "")[:50],
            )
            return False

        # Title length check
        if len(paper.get("title", "")) < 10:
            logger.warning(
                "validation_failed_title_too_short",
                title=paper.get("title", ""),
            )
            return False

        # At least one author
        if len(paper.get("authors", [])) == 0:
            logger.warning(
                "validation_failed_no_authors",
                title=paper.get("title", "")[:50],
            )
            return False

        return True

    def _generate_fingerprints(self, paper: Dict) -> Dict[str, str]:
        """
        Generate fingerprints for deduplication.

        Args:
            paper: Normalized paper dictionary

        Returns:
            Dictionary of fingerprint hashes
        """
        fingerprints = {}

        # Title hash
        title = paper.get("title", "").lower().strip()
        fingerprints["title_hash"] = hashlib.sha256(
            title.encode("utf-8")
        ).hexdigest()

        # Abstract hash
        abstract = paper.get("abstract", "").lower().strip()
        if abstract:
            fingerprints["abstract_hash"] = hashlib.sha256(
                abstract.encode("utf-8")
            ).hexdigest()

        # Author hash (sorted to handle different orderings)
        authors = sorted([a.lower().strip() for a in paper.get("authors", [])])
        author_str = "|".join(authors)
        fingerprints["author_hash"] = hashlib.sha256(
            author_str.encode("utf-8")
        ).hexdigest()

        # Combined hash (title + first author)
        if authors:
            combined = f"{title}|{authors[0]}"
            fingerprints["combined_hash"] = hashlib.sha256(
                combined.encode("utf-8")
            ).hexdigest()

        return fingerprints


class PaperMerger:
    """Merge paper data from multiple sources."""

    def merge(self, papers: List[Dict]) -> Dict:
        """
        Merge multiple paper records into one.

        Prioritizes data from different sources:
        1. External IDs: Keep all unique IDs
        2. Metadata: Prefer Semantic Scholar for citation counts, arXiv for categories
        3. Text: Prefer longer abstracts, cleaner titles

        Args:
            papers: List of paper dictionaries to merge

        Returns:
            Merged paper dictionary
        """
        if len(papers) == 1:
            return papers[0]

        merged = {}

        # Collect all external IDs
        merged["arxiv_id"] = self._first_non_null(papers, "arxiv_id")
        merged["doi"] = self._first_non_null(papers, "doi")
        merged["semantic_scholar_id"] = self._first_non_null(
            papers, "semantic_scholar_id"
        )

        # Text fields - prefer longer, cleaner versions
        merged["title"] = self._longest_string(papers, "title")
        merged["abstract"] = self._longest_string(papers, "abstract")

        # Authors - prefer longest list
        merged["authors"] = self._longest_list(papers, "authors")

        # Dates - prefer earliest published date
        merged["published_at"] = self._earliest_date(papers, "published_at")
        merged["updated_at"] = self._latest_date(papers, "updated_at")

        # Categories - merge all unique categories
        all_categories = []
        for paper in papers:
            all_categories.extend(paper.get("categories", []))
        merged["categories"] = list(set(all_categories))
        merged["primary_category"] = self._first_non_null(papers, "primary_category")

        # Metrics - prefer maximum values
        merged["citation_count"] = max(
            (p.get("citation_count", 0) for p in papers), default=0
        )
        merged["references_count"] = max(
            (p.get("references_count", 0) for p in papers), default=0
        )

        # URLs
        merged["pdf_url"] = self._first_non_null(papers, "pdf_url")
        merged["source_url"] = self._first_non_null(papers, "source_url")

        # Additional data - merge all
        merged["semantic_scholar_data"] = self._first_non_null(
            papers, "semantic_scholar_data"
        )

        # Processing status
        merged["processing_status"] = "pending"
        merged["data_source"] = "merged"

        return merged

    def _first_non_null(self, papers: List[Dict], key: str):
        """Get first non-null value for key."""
        for paper in papers:
            value = paper.get(key)
            if value:
                return value
        return None

    def _longest_string(self, papers: List[Dict], key: str) -> str:
        """Get longest string value for key."""
        values = [p.get(key, "") for p in papers]
        return max(values, key=len, default="")

    def _longest_list(self, papers: List[Dict], key: str) -> List:
        """Get longest list value for key."""
        values = [p.get(key, []) for p in papers]
        return max(values, key=len, default=[])

    def _earliest_date(self, papers: List[Dict], key: str) -> Optional[datetime]:
        """Get earliest date for key."""
        dates = [p.get(key) for p in papers if p.get(key)]
        return min(dates, default=None) if dates else None

    def _latest_date(self, papers: List[Dict], key: str) -> Optional[datetime]:
        """Get latest date for key."""
        dates = [p.get(key) for p in papers if p.get(key)]
        return max(dates, default=None) if dates else None

"""arXiv paper collector."""

import arxiv
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from paperpulse.config.settings import settings

logger = structlog.get_logger()


class ArxivCollector:
    """Collector for arXiv papers."""

    def __init__(self):
        self.max_results = settings.ARXIV_MAX_RESULTS
        self.query_interval = settings.ARXIV_QUERY_INTERVAL
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=self.query_interval,
            num_retries=3,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def collect_papers(
        self,
        query: str,
        max_results: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Collect papers from arXiv based on query.

        Args:
            query: Search query (e.g., "cat:cs.AI OR cat:cs.LG")
            max_results: Maximum number of papers to fetch
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of paper metadata dictionaries
        """
        max_results = max_results or self.max_results

        # Build search query
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        try:
            logger.info(
                "arxiv_collection_started",
                query=query,
                max_results=max_results,
            )

            for result in self.client.results(search):
                # Filter by date if specified
                if start_date and result.published < start_date:
                    continue
                if end_date and result.published > end_date:
                    continue

                paper_data = self._extract_metadata(result)
                papers.append(paper_data)

            logger.info(
                "arxiv_collection_completed",
                query=query,
                papers_collected=len(papers),
            )

        except Exception as e:
            logger.error(
                "arxiv_collection_failed",
                query=query,
                error=str(e),
                exc_info=True,
            )
            raise

        return papers

    def collect_recent_ai_papers(
        self, days_back: int = 7, categories: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Collect recent AI/ML papers from arXiv.

        Args:
            days_back: How many days back to search
            categories: List of arXiv categories (default: AI/ML categories)

        Returns:
            List of paper metadata dictionaries
        """
        if categories is None:
            categories = [
                "cs.AI",  # Artificial Intelligence
                "cs.LG",  # Machine Learning
                "cs.CL",  # Computation and Language
                "cs.CV",  # Computer Vision
                "cs.NE",  # Neural and Evolutionary Computing
                "stat.ML",  # Machine Learning (Statistics)
            ]

        # Build query for multiple categories
        query_parts = [f"cat:{cat}" for cat in categories]
        query = " OR ".join(query_parts)

        start_date = datetime.now() - timedelta(days=days_back)

        return self.collect_papers(
            query=query,
            start_date=start_date,
        )

    def collect_by_arxiv_ids(self, arxiv_ids: List[str]) -> List[Dict]:
        """
        Fetch specific papers by arXiv IDs.

        Args:
            arxiv_ids: List of arXiv IDs (e.g., ["2301.12345", "2302.67890"])

        Returns:
            List of paper metadata dictionaries
        """
        papers = []

        try:
            search = arxiv.Search(id_list=arxiv_ids)

            for result in self.client.results(search):
                paper_data = self._extract_metadata(result)
                papers.append(paper_data)

            logger.info(
                "arxiv_batch_collection_completed",
                requested_ids=len(arxiv_ids),
                papers_collected=len(papers),
            )

        except Exception as e:
            logger.error(
                "arxiv_batch_collection_failed",
                arxiv_ids=arxiv_ids,
                error=str(e),
                exc_info=True,
            )
            raise

        return papers

    def _extract_metadata(self, result: arxiv.Result) -> Dict:
        """
        Extract and normalize metadata from arXiv result.

        Args:
            result: arXiv API result object

        Returns:
            Normalized paper metadata dictionary
        """
        # Extract arXiv ID (remove version if present)
        arxiv_id = result.entry_id.split("/")[-1]
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.split("v")[0]

        return {
            "arxiv_id": arxiv_id,
            "title": result.title,
            "abstract": result.summary,
            "authors": [author.name for author in result.authors],
            "published_at": result.published,
            "updated_at": result.updated,
            "categories": result.categories,
            "primary_category": result.primary_category,
            "pdf_url": result.pdf_url,
            "source_url": result.entry_id,
            "doi": result.doi,
            "journal": result.journal_ref,
            # Additional metadata
            "comment": result.comment,
            "links": [link.href for link in result.links],
            # Source tracking
            "data_source": "arxiv",
            "ingested_at": datetime.utcnow(),
        }

    def get_paper_details(self, arxiv_id: str) -> Optional[Dict]:
        """
        Get detailed information for a single paper.

        Args:
            arxiv_id: arXiv ID

        Returns:
            Paper metadata dictionary or None if not found
        """
        papers = self.collect_by_arxiv_ids([arxiv_id])
        return papers[0] if papers else None

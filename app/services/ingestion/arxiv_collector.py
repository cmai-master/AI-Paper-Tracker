"""
arXiv API collector
"""

import time
import logging
from typing import List, Optional
from datetime import datetime, timedelta

import arxiv

from app.services.ingestion.schemas import RawPaper, Author, DataSource
from app.core.config import settings

logger = logging.getLogger(__name__)


class ArxivCollector:
    """arXiv API 수집기"""

    CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.NE", "stat.ML"]

    def __init__(self):
        self.client = arxiv.Client(
            page_size=settings.arxiv_max_results,
            delay_seconds=settings.arxiv_rate_limit_delay,
            num_retries=3,
        )

    def collect_since(self, since: datetime) -> List[RawPaper]:
        """
        Collect papers since a specific datetime

        Args:
            since: Collect papers published after this datetime

        Returns:
            List of raw papers
        """
        logger.info(f"Collecting arXiv papers since {since}")

        # Build query
        category_query = " OR ".join([f"cat:{cat}" for cat in self.CATEGORIES])
        date_filter = since.strftime("%Y%m%d%H%M%S")
        query = f"({category_query}) AND submittedDate:[{date_filter} TO *]"

        logger.debug(f"arXiv query: {query}")

        search = arxiv.Search(
            query=query,
            max_results=1000,  # Will paginate automatically
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        try:
            for result in self.client.results(search):
                try:
                    paper = self._convert_to_raw_paper(result)
                    papers.append(paper)
                    logger.debug(f"Collected: {paper.title[:50]}...")
                except Exception as e:
                    logger.error(f"Error converting arXiv result: {e}", exc_info=True)
                    continue

            logger.info(f"✅ Collected {len(papers)} papers from arXiv")
            return papers

        except Exception as e:
            logger.error(f"❌ arXiv collection failed: {e}", exc_info=True)
            raise

    def collect_recent(self, days: int = 1) -> List[RawPaper]:
        """
        Collect recent papers from the last N days

        Args:
            days: Number of days to look back

        Returns:
            List of raw papers
        """
        since = datetime.utcnow() - timedelta(days=days)
        return self.collect_since(since)

    def get_paper_by_id(self, arxiv_id: str) -> Optional[RawPaper]:
        """
        Get a specific paper by arXiv ID

        Args:
            arxiv_id: arXiv paper ID (e.g., "2311.12345")

        Returns:
            Raw paper or None if not found
        """
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            result = next(self.client.results(search))
            return self._convert_to_raw_paper(result)
        except StopIteration:
            logger.warning(f"Paper not found: {arxiv_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching paper {arxiv_id}: {e}")
            return None

    def _convert_to_raw_paper(self, result: arxiv.Result) -> RawPaper:
        """
        Convert arXiv Result to RawPaper

        Args:
            result: arXiv API result

        Returns:
            RawPaper object
        """
        # Extract arXiv ID from entry_id
        arxiv_id = result.entry_id.split("/")[-1]
        if "v" in arxiv_id:
            # Remove version suffix (e.g., "2311.12345v2" -> "2311.12345")
            arxiv_id = arxiv_id.split("v")[0]

        return RawPaper(
            source=DataSource.ARXIV,
            external_id=arxiv_id,
            title=result.title,
            abstract=result.summary,
            authors=[Author(name=author.name) for author in result.authors],
            published_at=result.published,
            updated_at=result.updated,
            categories=result.categories,
            pdf_url=result.pdf_url,
            raw_metadata={
                "entry_id": result.entry_id,
                "comment": result.comment,
                "journal_ref": result.journal_ref,
                "primary_category": result.primary_category,
                "doi": result.doi,
            },
        )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    collector = ArxivCollector()

    # Collect papers from the last day
    papers = collector.collect_recent(days=1)

    print(f"\n✅ Collected {len(papers)} papers")
    if papers:
        print(f"\nFirst paper:")
        print(f"  Title: {papers[0].title}")
        print(f"  Authors: {', '.join([a.name for a in papers[0].authors[:3]])}")
        print(f"  Published: {papers[0].published_at}")
        print(f"  Categories: {papers[0].categories}")

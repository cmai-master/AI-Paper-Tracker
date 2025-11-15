"""Semantic Scholar API collector."""

import httpx
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from paperpulse.config.settings import settings

logger = structlog.get_logger()


class SemanticScholarCollector:
    """Collector for Semantic Scholar papers."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        self.api_key = settings.SEMANTIC_SCHOLAR_API_KEY
        self.rate_limit = settings.SEMANTIC_SCHOLAR_RATE_LIMIT
        self.headers = {}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        fields: Optional[List[str]] = None,
        year: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search papers on Semantic Scholar.

        Args:
            query: Search query
            limit: Maximum number of results
            fields: Fields to retrieve
            year: Filter by year (e.g., "2024" or "2023-2024")

        Returns:
            List of paper metadata dictionaries
        """
        if fields is None:
            fields = [
                "paperId",
                "externalIds",
                "title",
                "abstract",
                "year",
                "authors",
                "venue",
                "publicationDate",
                "citationCount",
                "referenceCount",
                "fieldsOfStudy",
                "s2FieldsOfStudy",
                "publicationTypes",
                "journal",
                "openAccessPdf",
            ]

        params = {
            "query": query,
            "limit": min(limit, 100),  # API max is 100 per request
            "fields": ",".join(fields),
        }

        if year:
            params["year"] = year

        papers = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                offset = 0
                total_collected = 0

                while total_collected < limit:
                    params["offset"] = offset

                    response = await client.get(
                        f"{self.BASE_URL}/paper/search",
                        params=params,
                        headers=self.headers,
                    )
                    response.raise_for_status()

                    data = response.json()
                    results = data.get("data", [])

                    if not results:
                        break

                    for paper in results:
                        normalized = self._normalize_paper(paper)
                        papers.append(normalized)

                    total_collected += len(results)
                    offset += len(results)

                    # Rate limiting
                    await asyncio.sleep(1.0)

                    logger.info(
                        "semantic_scholar_batch_collected",
                        query=query,
                        batch_size=len(results),
                        total_collected=total_collected,
                    )

                    # Check if there are more results
                    if len(results) < params["limit"]:
                        break

            logger.info(
                "semantic_scholar_search_completed",
                query=query,
                papers_collected=len(papers),
            )

        except Exception as e:
            logger.error(
                "semantic_scholar_search_failed",
                query=query,
                error=str(e),
                exc_info=True,
            )
            raise

        return papers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_paper_by_id(
        self, paper_id: str, fields: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Get paper details by Semantic Scholar ID or external ID.

        Args:
            paper_id: Semantic Scholar ID or external ID (e.g., "arXiv:2301.12345")
            fields: Fields to retrieve

        Returns:
            Paper metadata dictionary or None if not found
        """
        if fields is None:
            fields = [
                "paperId",
                "externalIds",
                "title",
                "abstract",
                "year",
                "authors",
                "venue",
                "publicationDate",
                "citationCount",
                "referenceCount",
                "influentialCitationCount",
                "fieldsOfStudy",
                "s2FieldsOfStudy",
                "publicationTypes",
                "journal",
                "openAccessPdf",
                "citations",
                "references",
            ]

        params = {"fields": ",".join(fields)}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/paper/{paper_id}",
                    params=params,
                    headers=self.headers,
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                paper = response.json()

                return self._normalize_paper(paper)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(
                "semantic_scholar_get_paper_failed",
                paper_id=paper_id,
                error=str(e),
            )
            raise

    async def enrich_arxiv_paper(self, arxiv_id: str) -> Optional[Dict]:
        """
        Enrich arXiv paper with Semantic Scholar data.

        Args:
            arxiv_id: arXiv ID (e.g., "2301.12345")

        Returns:
            Enriched paper metadata or None if not found
        """
        # Semantic Scholar expects arXiv IDs in format "arXiv:2301.12345"
        s2_id = f"arXiv:{arxiv_id}"
        return await self.get_paper_by_id(s2_id)

    async def get_citations(
        self, paper_id: str, limit: int = 100
    ) -> List[Dict]:
        """
        Get papers that cite this paper.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of citations to retrieve

        Returns:
            List of citing papers
        """
        citations = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                offset = 0

                while len(citations) < limit:
                    params = {
                        "fields": "paperId,title,year,authors,citationCount",
                        "limit": min(100, limit - len(citations)),
                        "offset": offset,
                    }

                    response = await client.get(
                        f"{self.BASE_URL}/paper/{paper_id}/citations",
                        params=params,
                        headers=self.headers,
                    )
                    response.raise_for_status()

                    data = response.json()
                    results = data.get("data", [])

                    if not results:
                        break

                    for item in results:
                        if "citingPaper" in item:
                            citations.append(item["citingPaper"])

                    offset += len(results)
                    await asyncio.sleep(1.0)

                    if len(results) < params["limit"]:
                        break

        except Exception as e:
            logger.error(
                "get_citations_failed",
                paper_id=paper_id,
                error=str(e),
            )
            raise

        return citations

    async def get_references(
        self, paper_id: str, limit: int = 100
    ) -> List[Dict]:
        """
        Get papers referenced by this paper.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of references to retrieve

        Returns:
            List of referenced papers
        """
        references = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                offset = 0

                while len(references) < limit:
                    params = {
                        "fields": "paperId,title,year,authors,citationCount",
                        "limit": min(100, limit - len(references)),
                        "offset": offset,
                    }

                    response = await client.get(
                        f"{self.BASE_URL}/paper/{paper_id}/references",
                        params=params,
                        headers=self.headers,
                    )
                    response.raise_for_status()

                    data = response.json()
                    results = data.get("data", [])

                    if not results:
                        break

                    for item in results:
                        if "citedPaper" in item:
                            references.append(item["citedPaper"])

                    offset += len(results)
                    await asyncio.sleep(1.0)

                    if len(results) < params["limit"]:
                        break

        except Exception as e:
            logger.error(
                "get_references_failed",
                paper_id=paper_id,
                error=str(e),
            )
            raise

        return references

    def _normalize_paper(self, paper: Dict) -> Dict:
        """
        Normalize Semantic Scholar paper data to our schema.

        Args:
            paper: Raw paper data from Semantic Scholar

        Returns:
            Normalized paper metadata dictionary
        """
        external_ids = paper.get("externalIds", {})

        # Extract authors
        authors = []
        for author in paper.get("authors", []):
            authors.append(author.get("name", "Unknown"))

        # Extract publication date
        pub_date = paper.get("publicationDate")
        if pub_date:
            try:
                published_at = datetime.fromisoformat(pub_date)
            except ValueError:
                published_at = None
        else:
            # Fall back to year if available
            year = paper.get("year")
            if year:
                published_at = datetime(year, 1, 1)
            else:
                published_at = None

        # Extract PDF URL
        pdf_url = None
        open_access = paper.get("openAccessPdf")
        if open_access:
            pdf_url = open_access.get("url")

        return {
            "semantic_scholar_id": paper.get("paperId"),
            "arxiv_id": external_ids.get("ArXiv"),
            "doi": external_ids.get("DOI"),
            "title": paper.get("title"),
            "abstract": paper.get("abstract"),
            "authors": authors,
            "published_at": published_at,
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "journal": paper.get("journal", {}).get("name") if paper.get("journal") else None,
            "citation_count": paper.get("citationCount", 0),
            "references_count": paper.get("referenceCount", 0),
            "influential_citation_count": paper.get("influentialCitationCount", 0),
            "fields_of_study": paper.get("fieldsOfStudy", []),
            "s2_fields_of_study": [
                field.get("category") for field in paper.get("s2FieldsOfStudy", [])
            ],
            "publication_types": paper.get("publicationTypes", []),
            "pdf_url": pdf_url,
            # Store full data for later enrichment
            "semantic_scholar_data": paper,
            # Source tracking
            "data_source": "semantic_scholar",
            "ingested_at": datetime.utcnow(),
        }

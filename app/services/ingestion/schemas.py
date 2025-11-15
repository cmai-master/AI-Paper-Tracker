"""
Data models for ingestion module
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator


class DataSource(str, Enum):
    """Data source enumeration"""

    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PAPERS_WITH_CODE = "papers_with_code"
    TWITTER = "twitter"


class ProcessingStatus(str, Enum):
    """Processing status enumeration"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Author(BaseModel):
    """Author information"""

    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None


class RawPaper(BaseModel):
    """Raw paper data from external source"""

    source: DataSource
    external_id: str
    title: str
    abstract: Optional[str]
    authors: List[Author]
    published_at: datetime
    updated_at: Optional[datetime] = None
    categories: List[str] = Field(default_factory=list)
    pdf_url: Optional[str] = None
    raw_metadata: Dict = Field(default_factory=dict)

    @validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Validate title is not empty"""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()

    @validator("authors")
    @classmethod
    def authors_not_empty(cls, v: List[Author]) -> List[Author]:
        """Validate authors list is not empty"""
        if not v:
            raise ValueError("Authors list cannot be empty")
        return v


class NormalizedPaper(BaseModel):
    """Normalized paper data"""

    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    semantic_scholar_id: Optional[str] = None

    title: str
    abstract: Optional[str] = None
    authors: List[Author]

    published_at: datetime
    updated_at: Optional[datetime] = None
    version: int = 1

    categories: List[str]
    primary_category: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

    pdf_url: Optional[str] = None
    abstract_url: Optional[str] = None

    data_source: DataSource
    processing_status: ProcessingStatus = ProcessingStatus.PENDING

    # Fingerprints for deduplication
    title_hash: str = ""
    abstract_hash: Optional[str] = None
    author_hash: str = ""

    def compute_hashes(self) -> None:
        """Compute hashes for deduplication"""
        import hashlib

        # Title hash
        self.title_hash = hashlib.sha256(self.title.lower().strip().encode()).hexdigest()

        # Abstract hash
        if self.abstract:
            self.abstract_hash = hashlib.sha256(
                self.abstract.lower().strip().encode()
            ).hexdigest()

        # Author hash (sorted author names)
        author_str = "|".join(sorted(a.name.lower() for a in self.authors))
        self.author_hash = hashlib.sha256(author_str.encode()).hexdigest()


class IngestionStats(BaseModel):
    """Ingestion statistics"""

    source: str
    papers_collected: int
    papers_stored: int
    duplicates_found: int
    errors: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

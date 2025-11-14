"""Paper-related Pydantic schemas"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PaperBase(BaseModel):
    """Base paper schema"""

    arxiv_id: str = Field(..., description="arXiv ID")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    authors: List[str] = Field(..., description="List of authors")
    categories: List[str] = Field(..., description="arXiv categories")


class PaperCreate(PaperBase):
    """Schema for creating a new paper"""

    published_date: datetime = Field(..., description="Publication date")
    updated_date: Optional[datetime] = Field(None, description="Last update date")
    doi: Optional[str] = Field(None, description="DOI")
    pdf_url: Optional[str] = Field(None, description="PDF URL")


class PaperResponse(PaperBase):
    """Schema for paper response"""

    id: int
    published_date: datetime
    updated_date: Optional[datetime] = None
    doi: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    citation_count: int = 0
    influential_citation_count: int = 0
    is_processed: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaperSearchRequest(BaseModel):
    """Schema for search request"""

    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(default=10, ge=1, le=100, description="Number of results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")


class PaperSearchResultItem(BaseModel):
    """Single search result item"""

    paper: PaperResponse
    score: float = Field(..., description="Relevance score")
    highlights: Optional[List[str]] = Field(None, description="Text highlights")


class PaperSearchResponse(BaseModel):
    """Schema for search response"""

    results: List[PaperSearchResultItem]
    total: int = Field(..., description="Total number of matching papers")
    limit: int
    offset: int
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")

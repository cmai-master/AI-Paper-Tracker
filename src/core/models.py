"""
Core data models for PaperPulse
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class EntityType(str, Enum):
    """Knowledge graph entity types"""
    PAPER = "paper"
    CONCEPT = "concept"
    AUTHOR = "author"
    DATASET = "dataset"
    METHODOLOGY = "methodology"
    TASK = "task"
    METRIC = "metric"


class RelationType(str, Enum):
    """Knowledge graph relationship types"""
    CITES = "CITES"
    INTRODUCES = "INTRODUCES"
    USES = "USES"
    APPLIES = "APPLIES"
    IMPROVES = "IMPROVES"
    BUILDS_ON = "BUILDS_ON"
    RELATED_TO = "RELATED_TO"
    AUTHORED_BY = "AUTHORED_BY"
    COLLABORATES_WITH = "COLLABORATES_WITH"
    EVALUATED_ON = "EVALUATED_ON"


class SearchMode(str, Enum):
    """Search modes"""
    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"
    QA = "qa"
    COMPARISON = "comparison"


class NotificationChannel(str, Enum):
    """Notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    PUSH = "push"


class NotificationFrequency(str, Enum):
    """Notification frequency"""
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"


# Entity Models
class Entity(BaseModel):
    """Knowledge graph entity"""
    id: str
    entity_type: EntityType
    entity_id: str
    entity_name: str
    properties: Dict = Field(default_factory=dict)
    occurrence_count: int = 1
    importance_score: float = 0.0
    first_seen_at: Optional[datetime] = None
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)


class Relationship(BaseModel):
    """Knowledge graph relationship"""
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationType
    weight: float = 1.0
    confidence: float = 1.0
    context: Optional[str] = None
    paper_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Author(BaseModel):
    """Paper author"""
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None


class ProcessedDocument(BaseModel):
    """Processed paper document"""
    paper_id: str
    arxiv_id: str
    title: str
    abstract: str
    authors: List[Author]
    published_at: datetime
    categories: List[str] = []
    sections: Optional[List[Dict]] = None
    references: List[Dict] = []
    pdf_url: Optional[str] = None


# User & Notification Models
class NotificationSettings(BaseModel):
    """User notification settings"""
    channels: List[NotificationChannel]
    frequency: NotificationFrequency
    min_relevance_score: float = 0.7
    quiet_hours: tuple = (22, 8)


class UserProfile(BaseModel):
    """User profile"""
    user_id: str
    email: Optional[str] = None
    keywords: List[str] = []
    categories: List[str] = []
    followed_authors: List[str] = []
    interest_embedding: Optional[List[float]] = None
    notification_settings: NotificationSettings


class RecommendationResult(BaseModel):
    """Recommendation result"""
    paper_id: str
    title: str
    relevance_score: float
    reason: str
    strategy: str


# Search Models
class QueryAnalysis(BaseModel):
    """Query analysis result"""
    main_topic: str
    intent: str
    time_constraint: Optional[str] = None
    entities: List[str] = []


class Citation(BaseModel):
    """Citation in QA answer"""
    paper_id: str
    paper_title: str
    snippet: str


class QAResult(BaseModel):
    """Question answering result"""
    question: str
    answer: str
    citations: List[Citation]
    source_papers: List[str]
    confidence: float
    context_chunks: int


class SearchResult(BaseModel):
    """Search result"""
    papers: List[Dict]
    summary: str
    related_concepts: List[str] = []
    total_count: int


class ComparisonResult(BaseModel):
    """Comparison analysis result"""
    entities: List[str]
    aspects: List[str]
    comparison_table: Dict
    summary: str


class TrendAnalysis(BaseModel):
    """Trend analysis result"""
    concept: str
    yearly_counts: Dict[int, int]
    related_concepts: List[str]
    growth_rate: float
    trend_direction: str

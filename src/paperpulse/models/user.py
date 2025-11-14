"""User and user profile models."""

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from paperpulse.db.base import Base


class User(Base):
    """User account."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Profile info
    full_name = Column(String(255))
    affiliation = Column(String(255))  # University, company, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    interactions = relationship("UserInteraction", back_populates="user")
    recommendations = relationship("Recommendation", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class UserProfile(Base):
    """Extended user profile for personalization."""

    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)

    # Research interests
    interests = Column(ARRAY(String))  # Keywords/topics of interest
    research_areas = Column(ARRAY(String))  # Broader research areas
    favorite_authors = Column(ARRAY(String))  # Preferred authors

    # Notification preferences
    notification_frequency = Column(String(20), default="daily")  # daily, weekly, realtime
    notification_channels = Column(ARRAY(String), default=["email"])  # email, slack, push
    min_relevance_score = Column(Float, default=0.7)  # Minimum score for notifications

    # Paper preferences
    preferred_categories = Column(ARRAY(String))  # arXiv categories
    preferred_venues = Column(ARRAY(String))  # Conferences, journals
    excluded_keywords = Column(ARRAY(String))  # Keywords to avoid

    # Learning data
    interaction_count = Column(Integer, default=0)
    last_interaction_at = Column(DateTime)

    # Computed embeddings
    profile_embedding = Column(JSONB)  # Aggregated user interest embedding

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="profile")


class UserInteraction(Base):
    """User interactions with papers (for learning preferences)."""

    __tablename__ = "user_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True)

    # Interaction type
    interaction_type = Column(String(50), nullable=False)  # view, bookmark, download, cite, share
    interaction_value = Column(Float, default=1.0)  # Weight of interaction

    # Context
    source = Column(String(50))  # search, recommendation, notification, etc.
    query = Column(Text)  # Search query if applicable

    # Feedback
    explicit_rating = Column(Integer)  # 1-5 star rating if provided
    feedback = Column(String(20))  # positive, negative, neutral

    # Time spent (for implicit feedback)
    time_spent_seconds = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="interactions")
    paper = relationship("Paper", back_populates="user_interactions")

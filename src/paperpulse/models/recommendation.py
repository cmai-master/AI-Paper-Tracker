"""Recommendation and notification models."""

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from paperpulse.db.base import Base


class Recommendation(Base):
    """Paper recommendations for users."""

    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True)

    # Recommendation metadata
    recommendation_type = Column(String(50), nullable=False)  # profile_match, trending, cited_by_favorites, etc.
    relevance_score = Column(Float, nullable=False, index=True)  # 0-1 score
    ranking_position = Column(Integer)  # Position in recommendation list

    # Explanation
    explanation = Column(Text)  # Human-readable reason
    matching_keywords = Column(ARRAY(String))  # Keywords that matched

    # Status
    status = Column(String(20), default="pending")  # pending, sent, viewed, dismissed
    viewed_at = Column(DateTime)
    dismissed_at = Column(DateTime)

    # Feedback
    user_feedback = Column(String(20))  # helpful, not_helpful, irrelevant

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)  # When this recommendation expires

    # Relationships
    user = relationship("User", back_populates="recommendations")
    paper = relationship("Paper", back_populates="recommendations")


class Notification(Base):
    """User notifications."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Notification type
    notification_type = Column(String(50), nullable=False)  # new_papers, trending_topic, citation_alert, etc.

    # Content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB)  # Additional structured data (paper IDs, etc.)

    # Channels
    channels = Column(ARRAY(String))  # email, slack, push, in_app
    sent_via = Column(ARRAY(String))  # Which channels were actually used

    # Status
    status = Column(String(20), default="pending")  # pending, sent, delivered, failed, read
    sent_at = Column(DateTime)
    read_at = Column(DateTime)

    # Delivery tracking
    email_sent = Column(Boolean, default=False)
    slack_sent = Column(Boolean, default=False)
    push_sent = Column(Boolean, default=False)

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")

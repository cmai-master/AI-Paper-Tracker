"""User-related database models"""

from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """User account"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # User info
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    interactions: Mapped[List["UserInteraction"]] = relationship(
        "UserInteraction", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(email={self.email}, username={self.username})>"


class UserProfile(Base):
    """User profile and preferences"""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Research interests
    research_interests: Mapped[List[str]] = mapped_column(
        JSON, default=list
    )  # ["NLP", "Computer Vision", ...]
    preferred_categories: Mapped[List[str]] = mapped_column(
        JSON, default=list
    )  # ["cs.AI", "cs.CL", ...]
    keywords: Mapped[List[str]] = mapped_column(
        JSON, default=list
    )  # ["transformer", "attention", ...]

    # Interest embedding (learned from interactions)
    interest_embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(1024), nullable=True
    )

    # Notification preferences
    notification_settings: Mapped[dict] = mapped_column(
        JSON,
        default={
            "email": True,
            "slack": False,
            "frequency": "daily",  # instant, daily, weekly
            "min_relevance_score": 0.7,
        },
    )

    # Email/Slack
    slack_webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")

    __table_args__ = (
        Index(
            "idx_user_profile_interest_embedding",
            "interest_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )

    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id})>"


class UserInteraction(Base):
    """User interactions with papers (clicks, bookmarks, etc.)"""

    __tablename__ = "user_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Interaction type
    interaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # view, bookmark, download, cite, etc.

    # Interaction details
    relevance_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # User feedback (1-5 stars, etc.)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Additional context

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interactions")

    __table_args__ = (
        Index("idx_user_interactions_user_paper", user_id, paper_id),
        Index("idx_user_interactions_created_at", created_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<UserInteraction(user_id={self.user_id}, paper_id={self.paper_id}, type={self.interaction_type})>"

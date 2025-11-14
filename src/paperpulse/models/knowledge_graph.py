"""Knowledge graph models."""

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

from paperpulse.db.base import Base


class KGEntity(Base):
    """Knowledge graph entity (concept, method, dataset, etc.)."""

    __tablename__ = "kg_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Entity info
    entity_name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # concept, method, dataset, metric, person, organization
    normalized_name = Column(String(255), index=True)  # Normalized for deduplication

    # Description
    description = Column(Text)
    aliases = Column(ARRAY(String))  # Alternative names

    # Embedding
    embedding = Column(Vector(1024))  # Entity embedding for similarity

    # Statistics
    paper_count = Column(Integer, default=0)  # How many papers mention this
    importance_score = Column(Float, default=0.0)  # Computed importance

    # Metadata
    properties = Column(JSONB)  # Additional properties (e.g., year introduced, domain)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    outgoing_relationships = relationship(
        "KGRelationship",
        foreign_keys="KGRelationship.source_entity_id",
        back_populates="source_entity"
    )
    incoming_relationships = relationship(
        "KGRelationship",
        foreign_keys="KGRelationship.target_entity_id",
        back_populates="target_entity"
    )
    paper_associations = relationship("KGEntityPaper", back_populates="entity")


class KGRelationship(Base):
    """Relationships between entities."""

    __tablename__ = "kg_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source and target
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("kg_entities.id"), nullable=False, index=True)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("kg_entities.id"), nullable=False, index=True)

    # Relationship type
    relationship_type = Column(String(100), nullable=False, index=True)  # uses, extends, evaluates_on, compared_with, etc.
    relationship_subtype = Column(String(100))

    # Confidence and evidence
    confidence = Column(Float, default=1.0)  # Confidence in this relationship
    evidence_count = Column(Integer, default=1)  # How many papers support this

    # Description
    description = Column(Text)

    # Properties
    properties = Column(JSONB)  # Additional relationship properties

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source_entity = relationship(
        "KGEntity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships"
    )
    target_entity = relationship(
        "KGEntity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships"
    )


class KGEntityPaper(Base):
    """Many-to-many relationship between entities and papers."""

    __tablename__ = "kg_entity_papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    entity_id = Column(UUID(as_uuid=True), ForeignKey("kg_entities.id"), nullable=False, index=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True)

    # Context
    mention_count = Column(Integer, default=1)  # How many times mentioned
    context_snippets = Column(ARRAY(Text))  # Sentences mentioning the entity
    sections = Column(ARRAY(String))  # Which sections mention it

    # Relevance
    relevance_score = Column(Float, default=1.0)  # How relevant is this entity to the paper
    is_primary_topic = Column(Boolean, default=False)  # Is this a main topic of the paper

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    entity = relationship("KGEntity", back_populates="paper_associations")
    paper = relationship("Paper", back_populates="kg_entity_associations")

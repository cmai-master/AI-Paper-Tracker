"""Database models."""

from paperpulse.models.paper import (
    Paper,
    ProcessedDocument,
    PaperEmbedding,
    ChunkEmbedding,
    ExtractedReference,
)
from paperpulse.models.user import (
    User,
    UserProfile,
    UserInteraction,
)
from paperpulse.models.knowledge_graph import (
    KGEntity,
    KGRelationship,
    KGEntityPaper,
)
from paperpulse.models.recommendation import (
    Recommendation,
    Notification,
)
from paperpulse.models.chatbot import (
    ChatSession,
    ChatMessage,
)

__all__ = [
    # Paper models
    "Paper",
    "ProcessedDocument",
    "PaperEmbedding",
    "ChunkEmbedding",
    "ExtractedReference",
    # User models
    "User",
    "UserProfile",
    "UserInteraction",
    # Knowledge Graph models
    "KGEntity",
    "KGRelationship",
    "KGEntityPaper",
    # Recommendation models
    "Recommendation",
    "Notification",
    # Chatbot models
    "ChatSession",
    "ChatMessage",
]

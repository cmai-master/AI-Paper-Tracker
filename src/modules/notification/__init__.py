"""Notification & Recommendation Module"""

from .recommendation_engine import RecommendationEngine
from .relevance_scorer import RelevanceScorer
from .notification_dispatcher import NotificationDispatcher
from .notification_services import EmailService, SlackService

__all__ = [
    "RecommendationEngine",
    "RelevanceScorer",
    "NotificationDispatcher",
    "EmailService",
    "SlackService",
]

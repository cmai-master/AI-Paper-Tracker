"""FastAPI Server Module"""

from .app import create_app
from .routers import (
    search_router,
    recommendation_router,
    knowledge_graph_router,
    chatbot_router
)

__all__ = [
    "create_app",
    "search_router",
    "recommendation_router",
    "knowledge_graph_router",
    "chatbot_router",
]

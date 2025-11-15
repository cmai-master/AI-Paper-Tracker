"""
FastAPI Application
Main application setup and configuration
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None

from .routers import (
    search_router,
    recommendation_router,
    knowledge_graph_router,
    chatbot_router,
    health_router
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("Starting PaperPulse API server...")
    logger.info("Initializing services...")

    # Initialize services here
    # e.g., database connections, load models, etc.

    yield

    # Shutdown
    logger.info("Shutting down PaperPulse API server...")
    # Cleanup here


def create_app(config: Optional[dict] = None) -> FastAPI:
    """
    Create and configure FastAPI application

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured FastAPI application
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is not installed. Install with: pip install fastapi")

    # Create app
    app = FastAPI(
        title="PaperPulse API",
        description="AI-powered research paper tracking and exploration system",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/api/v1", tags=["Health"])
    app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])
    app.include_router(recommendation_router, prefix="/api/v1/recommendations", tags=["Recommendations"])
    app.include_router(knowledge_graph_router, prefix="/api/v1/knowledge-graph", tags=["Knowledge Graph"])
    app.include_router(chatbot_router, prefix="/api/v1/chat", tags=["Chatbot"])

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "PaperPulse API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }

    logger.info("FastAPI application created successfully")

    return app


# Create default app instance
if FASTAPI_AVAILABLE:
    app = create_app()
else:
    app = None
    logger.warning("FastAPI not available, app instance not created")

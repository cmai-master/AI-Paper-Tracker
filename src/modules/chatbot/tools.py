"""
Chatbot Tools
Tools that the chatbot can use to interact with the system
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SearchTool:
    """Tool for searching papers"""

    name = "search_papers"
    description = """Search for research papers based on a query.
    Use this when the user asks to find papers on a specific topic.

    Args:
        query (str): Search query
        top_k (int): Number of results to return (default: 10)
        mode (str): Search mode - 'vector', 'graph', or 'hybrid' (default: 'hybrid')

    Returns:
        List of relevant papers
    """

    def __init__(self, search_service):
        """Initialize search tool"""
        self.search_service = search_service

    async def run(
        self,
        query: str,
        top_k: int = 10,
        mode: str = "hybrid"
    ) -> Dict:
        """Execute search"""
        try:
            from src.core.models import SearchMode

            search_mode = SearchMode(mode)
            result = await self.search_service.search(
                query=query,
                mode=search_mode,
                top_k=top_k
            )

            return {
                "success": True,
                "papers": result.papers,
                "summary": result.summary,
                "total_count": result.total_count
            }

        except Exception as e:
            logger.error(f"Search tool failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "papers": []
            }


class RecommendTool:
    """Tool for getting personalized recommendations"""

    name = "get_recommendations"
    description = """Get personalized paper recommendations for the user.
    Use this when the user asks for recommendations or suggestions.

    Args:
        user_id (str): User ID
        n (int): Number of recommendations (default: 10)

    Returns:
        List of recommended papers
    """

    def __init__(self, recommendation_engine):
        """Initialize recommendation tool"""
        self.recommendation_engine = recommendation_engine

    async def run(
        self,
        user_id: str,
        n: int = 10
    ) -> Dict:
        """Execute recommendation"""
        try:
            # Get user profile (would normally query from DB)
            # For now, return mock recommendations
            recommendations = []

            return {
                "success": True,
                "recommendations": recommendations,
                "count": len(recommendations)
            }

        except Exception as e:
            logger.error(f"Recommendation tool failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "recommendations": []
            }


class CompareTool:
    """Tool for comparing papers or techniques"""

    name = "compare"
    description = """Compare two or more papers, techniques, or approaches.
    Use this when the user asks to compare things.

    Args:
        entities (List[str]): Entities to compare
        aspects (List[str]): Aspects to compare (optional)

    Returns:
        Comparison results
    """

    def __init__(self, comparison_engine):
        """Initialize comparison tool"""
        self.comparison_engine = comparison_engine

    async def run(
        self,
        entities: List[str],
        aspects: List[str] = None
    ) -> Dict:
        """Execute comparison"""
        try:
            if not aspects:
                aspects = ["approach", "performance", "limitations"]

            # Get papers for each entity (would query from DB/search)
            entity_papers = {entity: [] for entity in entities}

            result = await self.comparison_engine.compare(
                entities=entities,
                entity_papers=entity_papers,
                aspects=aspects
            )

            return {
                "success": True,
                "comparison_table": result.comparison_table,
                "summary": result.summary
            }

        except Exception as e:
            logger.error(f"Comparison tool failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class QATool:
    """Tool for answering questions"""

    name = "answer_question"
    description = """Answer a specific question about research based on papers.
    Use this when the user asks a specific question that requires detailed analysis.

    Args:
        question (str): Question to answer

    Returns:
        Answer with citations
    """

    def __init__(self, qa_engine):
        """Initialize QA tool"""
        self.qa_engine = qa_engine

    async def run(self, question: str) -> Dict:
        """Execute QA"""
        try:
            # Would retrieve relevant chunks first
            relevant_chunks = []

            result = await self.qa_engine.answer_question(
                question=question,
                relevant_chunks=relevant_chunks
            )

            return {
                "success": True,
                "answer": result.answer,
                "citations": result.citations,
                "confidence": result.confidence
            }

        except Exception as e:
            logger.error(f"QA tool failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "Failed to answer question"
            }


class TrendTool:
    """Tool for analyzing trends"""

    name = "analyze_trend"
    description = """Analyze research trends for a topic over time.
    Use this when the user asks about trends, evolution, or growth.

    Args:
        concept (str): Concept to analyze
        start_year (int): Start year (optional)
        end_year (int): End year (optional)

    Returns:
        Trend analysis results
    """

    def __init__(self, trend_analyzer):
        """Initialize trend tool"""
        self.trend_analyzer = trend_analyzer

    async def run(
        self,
        concept: str,
        start_year: int = None,
        end_year: int = None
    ) -> Dict:
        """Execute trend analysis"""
        try:
            # Would query papers from DB
            papers = []

            result = self.trend_analyzer.analyze_temporal_trend(
                concept=concept,
                papers=papers,
                start_year=start_year,
                end_year=end_year
            )

            return {
                "success": True,
                "yearly_counts": result.yearly_counts,
                "growth_rate": result.growth_rate,
                "trend_direction": result.trend_direction,
                "related_concepts": result.related_concepts
            }

        except Exception as e:
            logger.error(f"Trend tool failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

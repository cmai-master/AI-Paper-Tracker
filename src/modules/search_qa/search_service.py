"""
Search Service
Provides unified search interface with multiple modes
"""
import json
import logging
from typing import Optional, Dict, List

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.core.models import SearchMode, QueryAnalysis, SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """Unified search service supporting multiple modes"""

    def __init__(self, api_key: str = None):
        """Initialize search service"""
        if OPENAI_AVAILABLE and api_key:
            self.client = OpenAI(api_key=api_key)
            self.llm_available = True
        else:
            self.client = None
            self.llm_available = False
            logger.warning("OpenAI not available, query analysis will be limited")

    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        top_k: int = 10,
        filters: Optional[Dict] = None,
        vector_search_fn=None,
        graph_search_fn=None
    ) -> SearchResult:
        """
        Unified search interface

        Args:
            query: Search query
            mode: Search mode (vector, graph, hybrid, qa, comparison)
            top_k: Number of results
            filters: Optional filters (year, category, etc.)
            vector_search_fn: Function for vector search
            graph_search_fn: Function for graph search

        Returns:
            SearchResult object
        """
        # Analyze query
        query_analysis = await self._analyze_query(query)

        # Route to appropriate search method
        if mode == SearchMode.VECTOR:
            return await self._vector_search(query, top_k, filters, vector_search_fn)
        elif mode == SearchMode.GRAPH:
            return await self._graph_search(query_analysis, top_k, graph_search_fn)
        elif mode == SearchMode.HYBRID:
            return await self._hybrid_search(
                query,
                query_analysis,
                top_k,
                filters,
                vector_search_fn,
                graph_search_fn
            )
        else:
            # Default to vector search
            return await self._vector_search(query, top_k, filters, vector_search_fn)

    async def _analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query intent and extract entities"""
        if not self.llm_available:
            # Basic fallback analysis
            return QueryAnalysis(
                main_topic=query,
                intent="find_papers",
                time_constraint=None,
                entities=[]
            )

        prompt = f"""Analyze this research query:
Query: {query}

Extract:
1. Main topic/concept
2. Intent (find_papers, compare, explain, trend_analysis)
3. Time constraints (e.g., "recent", "2023", "last year")
4. Entities mentioned (techniques, datasets, authors)

Respond in JSON format:
{{
    "main_topic": "string",
    "intent": "string",
    "time_constraint": "string or null",
    "entities": ["entity1", "entity2"]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)

            return QueryAnalysis(
                main_topic=result.get("main_topic", query),
                intent=result.get("intent", "find_papers"),
                time_constraint=result.get("time_constraint"),
                entities=result.get("entities", [])
            )

        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return QueryAnalysis(
                main_topic=query,
                intent="find_papers",
                time_constraint=None,
                entities=[]
            )

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict],
        search_fn
    ) -> SearchResult:
        """Vector-based similarity search"""
        if not search_fn:
            logger.warning("No vector search function provided")
            return SearchResult(
                papers=[],
                summary="Vector search not available",
                related_concepts=[],
                total_count=0
            )

        try:
            # Call provided vector search function
            results = await search_fn(query, top_k=top_k, filters=filters)

            papers = results if isinstance(results, list) else results.get("papers", [])

            return SearchResult(
                papers=papers[:top_k],
                summary=f"Found {len(papers)} papers matching your query",
                related_concepts=[],
                total_count=len(papers)
            )

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return SearchResult(
                papers=[],
                summary=f"Search failed: {str(e)}",
                related_concepts=[],
                total_count=0
            )

    async def _graph_search(
        self,
        query_analysis: QueryAnalysis,
        top_k: int,
        search_fn
    ) -> SearchResult:
        """Graph-based search"""
        if not search_fn:
            logger.warning("No graph search function provided")
            return SearchResult(
                papers=[],
                summary="Graph search not available",
                related_concepts=[],
                total_count=0
            )

        try:
            results = await search_fn(query_analysis.main_topic, max_depth=2)

            papers = results.get("papers", []) if isinstance(results, dict) else results
            concepts = results.get("concepts", []) if isinstance(results, dict) else []

            return SearchResult(
                papers=papers[:top_k],
                summary=f"Found {len(papers)} papers via knowledge graph",
                related_concepts=concepts,
                total_count=len(papers)
            )

        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return SearchResult(
                papers=[],
                summary=f"Graph search failed: {str(e)}",
                related_concepts=[],
                total_count=0
            )

    async def _hybrid_search(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        top_k: int,
        filters: Optional[Dict],
        vector_search_fn,
        graph_search_fn
    ) -> SearchResult:
        """Hybrid search combining vector and graph approaches"""
        # Get results from both methods
        vector_results = await self._vector_search(
            query,
            top_k * 2,
            filters,
            vector_search_fn
        ) if vector_search_fn else None

        graph_results = await self._graph_search(
            query_analysis,
            top_k * 2,
            graph_search_fn
        ) if graph_search_fn else None

        # Combine results using RRF (Reciprocal Rank Fusion)
        combined_papers = self._reciprocal_rank_fusion(
            [
                vector_results.papers if vector_results else [],
                graph_results.papers if graph_results else []
            ],
            weights=[0.7, 0.3]
        )

        # Collect related concepts
        related_concepts = []
        if graph_results:
            related_concepts.extend(graph_results.related_concepts)

        # Generate summary
        summary = await self._generate_search_summary(query, combined_papers[:5])

        return SearchResult(
            papers=combined_papers[:top_k],
            summary=summary,
            related_concepts=related_concepts[:10],
            total_count=len(combined_papers)
        )

    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict]],
        weights: List[float],
        k: int = 60
    ) -> List[Dict]:
        """
        Combine multiple ranked lists using RRF

        Args:
            result_lists: List of ranked result lists
            weights: Weight for each list
            k: RRF parameter (default 60)

        Returns:
            Combined ranked list
        """
        scores = {}
        paper_objects = {}

        for result_list, weight in zip(result_lists, weights):
            for rank, paper in enumerate(result_list, start=1):
                paper_id = paper.get("id", str(rank))
                rrf_score = weight / (k + rank)

                if paper_id in scores:
                    scores[paper_id] += rrf_score
                else:
                    scores[paper_id] = rrf_score
                    paper_objects[paper_id] = paper

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [paper_objects[pid] for pid in sorted_ids]

    async def _generate_search_summary(
        self,
        query: str,
        top_papers: List[Dict]
    ) -> str:
        """Generate a summary of search results"""
        if not self.llm_available or not top_papers:
            return f"Found {len(top_papers)} relevant papers"

        # Create summary of top papers
        paper_summaries = []
        for i, paper in enumerate(top_papers[:3], 1):
            paper_summaries.append(
                f"{i}. {paper.get('title', 'Untitled')} - {paper.get('abstract', '')[:100]}..."
            )

        prompt = f"""Based on these search results for the query "{query}", provide a brief 2-3 sentence summary:

{chr(10).join(paper_summaries)}

Summary:"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.5
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return f"Found {len(top_papers)} papers related to {query}"

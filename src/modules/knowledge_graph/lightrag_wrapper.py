"""
LightRAG Integration Wrapper
Provides graph-based RAG capabilities
"""
import logging
from typing import Optional
from pathlib import Path

try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm import openai_complete_if_cache, openai_embedding
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    LightRAG = None
    QueryParam = None

from src.core.models import ProcessedDocument

logger = logging.getLogger(__name__)


class PaperLightRAG:
    """LightRAG wrapper for paper knowledge graph"""

    def __init__(self, working_dir: str = "./paper_kg", api_key: str = None):
        """Initialize LightRAG"""
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        if not LIGHTRAG_AVAILABLE:
            logger.warning("LightRAG not installed, graph-based RAG will not be available")
            self.rag = None
            return

        try:
            self.rag = LightRAG(
                working_dir=str(self.working_dir),
                llm_model_func=self._llm_func,
                embedding_func=self._embedding_func
            )
            logger.info(f"LightRAG initialized at {self.working_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}")
            self.rag = None

    async def _llm_func(self, prompt, **kwargs):
        """LLM function for LightRAG"""
        return await openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            **kwargs
        )

    async def _embedding_func(self, texts):
        """Embedding function for LightRAG"""
        return await openai_embedding(
            texts,
            model="text-embedding-3-small"
        )

    def insert_paper(self, paper: ProcessedDocument):
        """Insert paper into knowledge graph"""
        if not self.rag:
            logger.warning("LightRAG not available, skipping insertion")
            return

        context = self._prepare_paper_context(paper)

        try:
            self.rag.insert(context)
            logger.info(f"Inserted paper {paper.arxiv_id} into knowledge graph")
        except Exception as e:
            logger.error(f"Failed to insert paper {paper.arxiv_id}: {e}")

    def _prepare_paper_context(self, paper: ProcessedDocument) -> str:
        """Prepare paper context for LightRAG"""
        parts = [
            f"Title: {paper.title}",
            f"Authors: {', '.join([a.name for a in paper.authors])}",
            f"Published: {paper.published_at.year}",
            f"Categories: {', '.join(paper.categories)}",
            f"\nAbstract:\n{paper.abstract}",
        ]

        # Add sections if available
        if paper.sections:
            for section in paper.sections[:3]:  # Limit to first 3 sections
                section_type = section.get("section_type", "unknown")
                content = section.get("content", "")[:1000]  # Limit length
                parts.append(f"\n{section_type}:\n{content}")

        return "\n\n".join(parts)

    def query_related_concepts(
        self,
        concept: str,
        mode: str = "hybrid"
    ) -> Optional[str]:
        """Query related concepts and papers"""
        if not self.rag:
            logger.warning("LightRAG not available")
            return None

        query = f"What papers and concepts are related to {concept}? Explain the relationships and key findings."

        try:
            if QueryParam:
                result = self.rag.query(
                    query,
                    param=QueryParam(mode=mode)
                )
            else:
                result = self.rag.query(query)
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None

    def trace_research_evolution(self, topic: str) -> Optional[str]:
        """Trace research evolution over time"""
        if not self.rag:
            return None

        query = f"Trace the evolution of research on {topic} chronologically. Highlight key papers and breakthroughs."

        try:
            if QueryParam:
                result = self.rag.query(
                    query,
                    param=QueryParam(mode="global")
                )
            else:
                result = self.rag.query(query)
            return result
        except Exception as e:
            logger.error(f"Evolution trace failed: {e}")
            return None

    def find_research_gaps(self, domain: str) -> Optional[str]:
        """Identify research gaps in a domain"""
        if not self.rag:
            return None

        query = f"Based on the papers in {domain}, what are the unexplored areas or research gaps? What questions remain unanswered?"

        try:
            if QueryParam:
                result = self.rag.query(
                    query,
                    param=QueryParam(mode="global")
                )
            else:
                result = self.rag.query(query)
            return result
        except Exception as e:
            logger.error(f"Research gap analysis failed: {e}")
            return None

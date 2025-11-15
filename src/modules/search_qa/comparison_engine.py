"""
Comparison Engine
Compare papers, techniques, or approaches
"""
import logging
from typing import List, Dict

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.core.models import ComparisonResult

logger = logging.getLogger(__name__)


class ComparisonEngine:
    """Engine for comparing papers and techniques"""

    def __init__(self, api_key: str = None):
        """Initialize comparison engine"""
        if OPENAI_AVAILABLE and api_key:
            self.client = OpenAI(api_key=api_key)
            self.llm_available = True
        else:
            self.client = None
            self.llm_available = False
            logger.warning("OpenAI not available, comparison will be limited")

    async def compare(
        self,
        entities: List[str],
        entity_papers: Dict[str, List[Dict]],
        aspects: List[str] = None
    ) -> ComparisonResult:
        """
        Compare multiple entities (papers/techniques/approaches)

        Args:
            entities: List of entity names to compare
            entity_papers: Dict mapping entity -> list of related papers
            aspects: Aspects to compare (e.g., approach, performance, limitations)

        Returns:
            ComparisonResult
        """
        if not aspects:
            aspects = ["approach", "performance", "limitations", "use_cases"]

        if not self.llm_available:
            return ComparisonResult(
                entities=entities,
                aspects=aspects,
                comparison_table={},
                summary="Comparison service not available - OpenAI API required"
            )

        # Build context for each entity
        entity_contexts = {}
        for entity in entities:
            papers = entity_papers.get(entity, [])
            entity_contexts[entity] = self._build_entity_context(papers)

        # Generate comparison
        prompt = self._build_comparison_prompt(entities, entity_contexts, aspects)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )

            comparison_text = response.choices[0].message.content

            # Parse into table format
            comparison_table = self._parse_comparison(comparison_text, entities, aspects)

            return ComparisonResult(
                entities=entities,
                aspects=aspects,
                comparison_table=comparison_table,
                summary=comparison_text
            )

        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return ComparisonResult(
                entities=entities,
                aspects=aspects,
                comparison_table={},
                summary=f"Comparison failed: {str(e)}"
            )

    def _build_entity_context(self, papers: List[Dict]) -> str:
        """Build context string for an entity from its papers"""
        if not papers:
            return "No papers available"

        context_parts = []

        for paper in papers[:3]:  # Limit to top 3 papers
            context_parts.append(
                f"Title: {paper.get('title', 'Unknown')}\n"
                f"Abstract: {paper.get('abstract', '')[:300]}..."
            )

        return "\n\n".join(context_parts)

    def _build_comparison_prompt(
        self,
        entities: List[str],
        contexts: Dict[str, str],
        aspects: List[str]
    ) -> str:
        """Build comparison prompt"""
        context_str = "\n\n".join([
            f"## {entity}\n{context}"
            for entity, context in contexts.items()
        ])

        return f"""Compare the following entities across the specified aspects:

Entities: {', '.join(entities)}
Aspects: {', '.join(aspects)}

Context:
{context_str[:3000]}

Provide a detailed comparison in the following format:

### Comparison Table

| Aspect | {' | '.join(entities)} |
|--------|{'|'.join(['---'] * len(entities))}|
{chr(10).join([f'| {aspect} | {" | ".join(["..." for _ in entities])} |' for aspect in aspects])}

### Summary
Provide a 2-3 paragraph summary highlighting:
1. Key differences between the entities
2. Strengths and weaknesses
3. Recommended use cases for each

Comparison:"""

    def _parse_comparison(
        self,
        comparison_text: str,
        entities: List[str],
        aspects: List[str]
    ) -> Dict:
        """Parse comparison text into structured table"""
        # Simple table structure
        table = {}

        for aspect in aspects:
            table[aspect] = {}
            for entity in entities:
                # Try to extract comparison for this aspect and entity
                # This is a simplified parser
                table[aspect][entity] = self._extract_aspect_entity(
                    comparison_text,
                    aspect,
                    entity
                )

        return table

    def _extract_aspect_entity(
        self,
        text: str,
        aspect: str,
        entity: str
    ) -> str:
        """Extract specific aspect-entity comparison from text"""
        # Simple extraction - look for aspect and entity mentions nearby
        lines = text.split('\n')

        relevant_lines = []
        for i, line in enumerate(lines):
            if aspect.lower() in line.lower() and entity.lower() in line.lower():
                # Found a relevant line
                relevant_lines.append(line)
                # Also include nearby lines
                if i > 0:
                    relevant_lines.append(lines[i-1])
                if i < len(lines) - 1:
                    relevant_lines.append(lines[i+1])

        if relevant_lines:
            return " ".join(relevant_lines)
        else:
            return "Not specified"

    async def compare_papers_directly(
        self,
        paper1: Dict,
        paper2: Dict,
        aspects: List[str] = None
    ) -> ComparisonResult:
        """Compare two papers directly"""
        if not aspects:
            aspects = ["methodology", "results", "contributions", "limitations"]

        entities = [
            paper1.get("title", "Paper 1"),
            paper2.get("title", "Paper 2")
        ]

        entity_papers = {
            entities[0]: [paper1],
            entities[1]: [paper2]
        }

        return await self.compare(entities, entity_papers, aspects)

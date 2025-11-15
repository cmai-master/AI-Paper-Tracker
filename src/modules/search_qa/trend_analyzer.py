"""
Trend Analyzer
Analyze research trends over time
"""
import logging
from typing import List, Dict
from collections import defaultdict

from src.core.models import TrendAnalysis

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyze research trends and evolution"""

    def analyze_temporal_trend(
        self,
        concept: str,
        papers: List[Dict],
        start_year: int = None,
        end_year: int = None
    ) -> TrendAnalysis:
        """
        Analyze temporal trend for a concept

        Args:
            concept: Concept to analyze
            papers: List of papers related to the concept
            start_year: Start year for analysis
            end_year: End year for analysis

        Returns:
            TrendAnalysis result
        """
        # Count papers by year
        yearly_counts = defaultdict(int)

        for paper in papers:
            year = self._extract_year(paper)
            if year and (not start_year or year >= start_year) and (not end_year or year <= end_year):
                yearly_counts[year] += 1

        if not yearly_counts:
            return TrendAnalysis(
                concept=concept,
                yearly_counts={},
                related_concepts=[],
                growth_rate=0.0,
                trend_direction="no_data"
            )

        # Calculate growth rate
        years_sorted = sorted(yearly_counts.keys())
        counts = [yearly_counts[y] for y in years_sorted]
        growth_rate = self._calculate_growth_rate(counts)

        # Determine trend direction
        if growth_rate > 0.1:
            trend_direction = "increasing"
        elif growth_rate < -0.1:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        # Extract related concepts from papers
        related_concepts = self._extract_related_concepts(papers)

        return TrendAnalysis(
            concept=concept,
            yearly_counts=dict(yearly_counts),
            related_concepts=related_concepts[:10],
            growth_rate=round(growth_rate, 3),
            trend_direction=trend_direction
        )

    def _extract_year(self, paper: Dict) -> int:
        """Extract year from paper"""
        published_at = paper.get("published_at")

        if not published_at:
            return None

        if isinstance(published_at, int):
            return published_at

        # Try to parse datetime
        try:
            if hasattr(published_at, 'year'):
                return published_at.year

            # Try parsing string
            from dateutil import parser
            dt = parser.parse(str(published_at))
            return dt.year
        except:
            return None

    def _calculate_growth_rate(self, counts: List[int]) -> float:
        """Calculate compound annual growth rate (CAGR)"""
        if len(counts) < 2:
            return 0.0

        first_count = counts[0]
        last_count = counts[-1]
        years = len(counts) - 1

        if first_count == 0:
            # Avoid division by zero
            if last_count > 0:
                return 1.0  # Maximum growth
            return 0.0

        # CAGR formula
        growth = ((last_count / first_count) ** (1 / years)) - 1

        return growth

    def _extract_related_concepts(self, papers: List[Dict]) -> List[str]:
        """Extract related concepts from papers"""
        # Simple extraction from titles and abstracts
        concept_freq = defaultdict(int)

        # Common ML/AI keywords to look for
        keywords = [
            "transformer", "bert", "gpt", "attention", "neural network",
            "deep learning", "reinforcement learning", "gan", "vae",
            "classification", "segmentation", "detection", "nlp",
            "computer vision", "lstm", "rnn", "cnn", "diffusion"
        ]

        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()

            for keyword in keywords:
                if keyword in text:
                    concept_freq[keyword] += 1

        # Sort by frequency
        sorted_concepts = sorted(
            concept_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [concept for concept, _ in sorted_concepts]

    def compare_trends(
        self,
        concepts: List[str],
        concept_papers: Dict[str, List[Dict]],
        start_year: int = None,
        end_year: int = None
    ) -> Dict[str, TrendAnalysis]:
        """
        Compare trends for multiple concepts

        Args:
            concepts: List of concepts to compare
            concept_papers: Dict mapping concept -> papers
            start_year: Start year
            end_year: End year

        Returns:
            Dict of concept -> TrendAnalysis
        """
        trends = {}

        for concept in concepts:
            papers = concept_papers.get(concept, [])
            trends[concept] = self.analyze_temporal_trend(
                concept,
                papers,
                start_year,
                end_year
            )

        return trends

    def identify_emerging_topics(
        self,
        papers: List[Dict],
        min_papers: int = 5,
        recent_years: int = 2
    ) -> List[Dict]:
        """
        Identify emerging research topics

        Args:
            papers: All papers
            min_papers: Minimum papers for a topic to be considered
            recent_years: Number of recent years to consider

        Returns:
            List of emerging topics with growth metrics
        """
        from datetime import datetime

        current_year = datetime.now().year
        cutoff_year = current_year - recent_years

        # Get recent and older papers
        recent_papers = [p for p in papers if self._extract_year(p) and self._extract_year(p) >= cutoff_year]
        older_papers = [p for p in papers if self._extract_year(p) and self._extract_year(p) < cutoff_year]

        # Extract concepts from both sets
        recent_concepts = self._extract_related_concepts(recent_papers)
        older_concepts = self._extract_related_concepts(older_papers)

        # Find concepts that are much more frequent in recent papers
        emerging = []

        recent_counts = defaultdict(int)
        for paper in recent_papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            for concept in recent_concepts:
                if concept in text:
                    recent_counts[concept] += 1

        older_counts = defaultdict(int)
        for paper in older_papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            for concept in older_concepts:
                if concept in text:
                    older_counts[concept] += 1

        for concept in recent_concepts:
            recent_count = recent_counts[concept]
            older_count = older_counts.get(concept, 0)

            if recent_count >= min_papers:
                # Calculate growth
                if older_count == 0:
                    growth = float('inf') if recent_count > 0 else 0
                else:
                    growth = (recent_count - older_count) / older_count

                if growth > 0.5:  # At least 50% growth
                    emerging.append({
                        "concept": concept,
                        "recent_count": recent_count,
                        "older_count": older_count,
                        "growth_rate": growth
                    })

        # Sort by growth rate
        emerging.sort(key=lambda x: x["growth_rate"], reverse=True)

        return emerging[:10]

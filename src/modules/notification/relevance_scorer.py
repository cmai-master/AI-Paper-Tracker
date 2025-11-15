"""
Relevance Scorer
Calculates relevance score between user profile and papers
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta
import numpy as np

from src.core.models import UserProfile

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Calculate user-paper relevance scores"""

    def calculate_score(
        self,
        paper: Dict,
        user: UserProfile,
        paper_embedding: List[float] = None
    ) -> float:
        """
        Calculate relevance score (0.0 - 1.0)

        Args:
            paper: Paper dictionary with metadata
            user: User profile
            paper_embedding: Paper's document embedding

        Returns:
            Relevance score between 0 and 1
        """
        scores = []
        weights = []

        # 1. Semantic similarity (40%) - if embeddings available
        if user.interest_embedding and paper_embedding:
            semantic_score = self._cosine_similarity(
                paper_embedding,
                user.interest_embedding
            )
            scores.append(semantic_score)
            weights.append(0.4)

        # 2. Keyword matching (25%)
        keyword_score = self._keyword_match(paper, user.keywords)
        scores.append(keyword_score)
        weights.append(0.25)

        # 3. Author following (15%)
        author_score = self._author_match(paper, user.followed_authors)
        scores.append(author_score)
        weights.append(0.15)

        # 4. Category matching (10%)
        category_score = self._category_match(paper, user.categories)
        scores.append(category_score)
        weights.append(0.1)

        # 5. Recency & trend (10%)
        recency_score = self._recency_score(paper)
        scores.append(recency_score)
        weights.append(0.1)

        # Weighted average
        if not scores:
            return 0.0

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        final_score = sum(s * w for s, w in zip(scores, normalized_weights))
        return min(max(final_score, 0.0), 1.0)

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)

            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)

        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0

    def _keyword_match(self, paper: Dict, keywords: List[str]) -> float:
        """Calculate keyword matching score"""
        if not keywords:
            return 0.5  # Neutral score

        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()

        matches = sum(1 for kw in keywords if kw.lower() in text)
        score = matches / len(keywords)

        return min(score, 1.0)

    def _author_match(self, paper: Dict, followed_authors: List[str]) -> float:
        """Check if any followed authors are in the paper"""
        if not followed_authors:
            return 0.0

        paper_authors = [a.get("name", "") for a in paper.get("authors", [])]

        for followed in followed_authors:
            if any(followed.lower() in author.lower() for author in paper_authors):
                return 1.0

        return 0.0

    def _category_match(self, paper: Dict, user_categories: List[str]) -> float:
        """Calculate category matching score"""
        if not user_categories:
            return 0.5  # Neutral

        paper_categories = paper.get("categories", [])
        if not paper_categories:
            return 0.0

        matches = len(set(paper_categories) & set(user_categories))
        score = matches / len(user_categories)

        return min(score, 1.0)

    def _recency_score(self, paper: Dict) -> float:
        """Calculate recency score"""
        published_at = paper.get("published_at")

        if not published_at:
            return 0.5

        if isinstance(published_at, str):
            try:
                from dateutil import parser
                published_at = parser.parse(published_at)
            except:
                return 0.5

        days_old = (datetime.utcnow() - published_at).days

        if days_old <= 1:
            return 1.0
        elif days_old <= 7:
            return 0.8
        elif days_old <= 30:
            return 0.5
        elif days_old <= 90:
            return 0.3
        else:
            return 0.2

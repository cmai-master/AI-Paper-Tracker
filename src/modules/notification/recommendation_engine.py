"""
Recommendation Engine
Multi-strategy hybrid recommendation system
"""
import logging
from typing import List, Dict, Tuple
from collections import defaultdict

from src.core.models import UserProfile, RecommendationResult
from .relevance_scorer import RelevanceScorer

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Hybrid recommendation engine"""

    def __init__(self):
        """Initialize recommendation engine"""
        self.relevance_scorer = RelevanceScorer()

    def get_recommendations(
        self,
        user: UserProfile,
        candidate_papers: List[Dict],
        n: int = 10,
        user_interactions: List[Dict] = None,
        similar_users: List[Tuple[UserProfile, float]] = None
    ) -> List[RecommendationResult]:
        """
        Generate recommendations using multiple strategies

        Args:
            user: User profile
            candidate_papers: List of candidate papers
            n: Number of recommendations to return
            user_interactions: User's interaction history
            similar_users: List of (similar_user, similarity_score) tuples

        Returns:
            List of recommendation results
        """
        # 1. Content-based recommendations
        content_recs = self._content_based_recommendations(
            user,
            candidate_papers,
            n * 2
        )

        # 2. Collaborative filtering (if similar users available)
        collab_recs = []
        if similar_users:
            collab_recs = self._collaborative_filtering(
                user,
                similar_users,
                candidate_papers,
                n * 2
            )

        # 3. Combine strategies
        if collab_recs:
            combined = self._combine_recommendations([
                (content_recs, 0.6),
                (collab_recs, 0.4)
            ])
        else:
            combined = content_recs

        # 4. Apply diversity optimization
        diverse = self._optimize_diversity(combined, n)

        return diverse[:n]

    def _content_based_recommendations(
        self,
        user: UserProfile,
        papers: List[Dict],
        n: int
    ) -> List[RecommendationResult]:
        """Content-based recommendations using user profile"""
        scored_papers = []

        for paper in papers:
            score = self.relevance_scorer.calculate_score(
                paper,
                user,
                paper.get("document_embedding")
            )

            if score >= user.notification_settings.min_relevance_score:
                scored_papers.append((paper, score))

        # Sort by score
        scored_papers.sort(key=lambda x: x[1], reverse=True)

        # Convert to recommendation results
        recommendations = []
        for paper, score in scored_papers[:n]:
            recommendations.append(RecommendationResult(
                paper_id=paper.get("id", ""),
                title=paper.get("title", ""),
                relevance_score=score,
                reason=self._generate_reason(paper, user, "content"),
                strategy="content_based"
            ))

        return recommendations

    def _collaborative_filtering(
        self,
        user: UserProfile,
        similar_users: List[Tuple[UserProfile, float]],
        candidate_papers: List[Dict],
        n: int
    ) -> List[RecommendationResult]:
        """Collaborative filtering based on similar users"""
        # Aggregate scores from similar users
        paper_scores = defaultdict(float)
        paper_count = defaultdict(int)

        for similar_user, similarity in similar_users:
            # Score each candidate paper for the similar user
            for paper in candidate_papers:
                score = self.relevance_scorer.calculate_score(
                    paper,
                    similar_user,
                    paper.get("document_embedding")
                )

                # Weight by user similarity
                weighted_score = score * similarity
                paper_scores[paper["id"]] += weighted_score
                paper_count[paper["id"]] += 1

        # Average scores
        averaged_scores = {}
        for paper_id, total_score in paper_scores.items():
            averaged_scores[paper_id] = total_score / paper_count[paper_id]

        # Sort and create recommendations
        sorted_papers = sorted(
            averaged_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]

        recommendations = []
        paper_dict = {p["id"]: p for p in candidate_papers}

        for paper_id, score in sorted_papers:
            paper = paper_dict.get(paper_id)
            if paper:
                recommendations.append(RecommendationResult(
                    paper_id=paper_id,
                    title=paper.get("title", ""),
                    relevance_score=score,
                    reason="Recommended by users with similar interests",
                    strategy="collaborative"
                ))

        return recommendations

    def _combine_recommendations(
        self,
        strategy_results: List[Tuple[List[RecommendationResult], float]]
    ) -> List[RecommendationResult]:
        """Combine recommendations from multiple strategies"""
        # Aggregate scores
        paper_scores = defaultdict(float)
        paper_recs = {}

        for recs, weight in strategy_results:
            for rec in recs:
                paper_scores[rec.paper_id] += rec.relevance_score * weight

                # Keep the recommendation object
                if rec.paper_id not in paper_recs:
                    paper_recs[rec.paper_id] = rec

        # Update scores and sort
        combined = []
        for paper_id, score in paper_scores.items():
            rec = paper_recs[paper_id]
            rec.relevance_score = min(score, 1.0)
            combined.append(rec)

        combined.sort(key=lambda x: x.relevance_score, reverse=True)
        return combined

    def _optimize_diversity(
        self,
        recommendations: List[RecommendationResult],
        target: int
    ) -> List[RecommendationResult]:
        """
        Optimize for diversity using MMR (Maximal Marginal Relevance)
        Ensures recommendations cover diverse topics
        """
        if len(recommendations) <= target:
            return recommendations

        selected = [recommendations[0]]
        remaining = recommendations[1:]

        while len(selected) < target and remaining:
            best_score = -1
            best_rec = None

            for rec in remaining:
                # Relevance component
                relevance = rec.relevance_score

                # Diversity component (simple title-based for now)
                max_similarity = max(
                    self._title_similarity(rec.title, s.title)
                    for s in selected
                )
                diversity = 1 - max_similarity

                # MMR score (balance relevance and diversity)
                mmr_score = 0.6 * relevance + 0.4 * diversity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_rec = rec

            if best_rec:
                selected.append(best_rec)
                remaining.remove(best_rec)
            else:
                break

        return selected

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Simple title similarity based on word overlap"""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _generate_reason(
        self,
        paper: Dict,
        user: UserProfile,
        strategy: str
    ) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []

        # Check keyword matches
        title_abstract = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        matched_keywords = [kw for kw in user.keywords if kw.lower() in title_abstract]
        if matched_keywords:
            reasons.append(f"matches your interests in {', '.join(matched_keywords[:3])}")

        # Check author match
        paper_authors = [a.get("name", "") for a in paper.get("authors", [])]
        for followed in user.followed_authors:
            if any(followed.lower() in author.lower() for author in paper_authors):
                reasons.append(f"by {followed} (followed author)")
                break

        # Check category match
        paper_categories = paper.get("categories", [])
        matched_cats = list(set(paper_categories) & set(user.categories))
        if matched_cats:
            reasons.append(f"in category {matched_cats[0]}")

        if reasons:
            return "Recommended: " + ", ".join(reasons)
        else:
            return "Recommended based on your profile"

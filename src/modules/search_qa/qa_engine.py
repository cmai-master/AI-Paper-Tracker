"""
QA Engine
Question answering with citations from research papers
"""
import re
import logging
from typing import List, Dict, Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.core.models import QAResult, Citation

logger = logging.getLogger(__name__)


class QAEngine:
    """Question answering engine with citation support"""

    def __init__(self, api_key: str = None):
        """Initialize QA engine"""
        if OPENAI_AVAILABLE and api_key:
            self.client = OpenAI(api_key=api_key)
            self.llm_available = True
        else:
            self.client = None
            self.llm_available = False
            logger.warning("OpenAI not available, QA will be limited")

    async def answer_question(
        self,
        question: str,
        relevant_chunks: List[Dict],
        max_context_papers: int = 5
    ) -> QAResult:
        """
        Answer a question using relevant paper chunks

        Args:
            question: User's question
            relevant_chunks: List of relevant text chunks from papers
            max_context_papers: Maximum number of papers to use as context

        Returns:
            QAResult with answer and citations
        """
        if not self.llm_available:
            return QAResult(
                question=question,
                answer="QA service not available - OpenAI API required",
                citations=[],
                source_papers=[],
                confidence=0.0,
                context_chunks=0
            )

        # Build context from chunks
        context_parts = []
        paper_ids = set()

        for chunk in relevant_chunks[:max_context_papers * 4]:
            paper_id = chunk.get("paper_id", "")
            if paper_id:
                paper_ids.add(paper_id)

            context_parts.append(
                f"[Paper: {chunk.get('paper_title', 'Unknown')}]\n{chunk.get('chunk_text', '')}\n"
            )

        if not context_parts:
            return QAResult(
                question=question,
                answer="No relevant papers found to answer this question.",
                citations=[],
                source_papers=[],
                confidence=0.0,
                context_chunks=0
            )

        context = "\n\n".join(context_parts)

        # Generate answer with citations
        prompt = f"""Based on the following research papers, answer the question.
Provide specific citations to papers using [Paper: title] format.
If the papers don't contain enough information, say so clearly.

Context:
{context[:4000]}  # Limit context length

Question: {question}

Answer (with citations):"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )

            answer = response.choices[0].message.content

            # Extract citations
            citations = self._extract_citations(answer, relevant_chunks)

            # Calculate confidence
            confidence = self._calculate_confidence(
                answer,
                relevant_chunks,
                len(paper_ids)
            )

            return QAResult(
                question=question,
                answer=answer,
                citations=citations,
                source_papers=list(paper_ids),
                confidence=confidence,
                context_chunks=len(context_parts)
            )

        except Exception as e:
            logger.error(f"QA failed: {e}")
            return QAResult(
                question=question,
                answer=f"Failed to generate answer: {str(e)}",
                citations=[],
                source_papers=[],
                confidence=0.0,
                context_chunks=len(context_parts)
            )

    def _extract_citations(
        self,
        answer: str,
        chunks: List[Dict]
    ) -> List[Citation]:
        """Extract citations from answer"""
        citations = []
        citation_pattern = r'\[Paper: ([^\]]+)\]'

        matches = re.findall(citation_pattern, answer)
        seen_papers = set()

        for title in matches:
            # Find matching chunk
            chunk = next(
                (c for c in chunks if title.lower() in c.get("paper_title", "").lower()),
                None
            )

            if chunk and chunk.get("paper_id") not in seen_papers:
                citations.append(Citation(
                    paper_id=chunk.get("paper_id", ""),
                    paper_title=chunk.get("paper_title", ""),
                    snippet=chunk.get("chunk_text", "")[:200] + "..."
                ))
                seen_papers.add(chunk.get("paper_id"))

        return citations

    def _calculate_confidence(
        self,
        answer: str,
        chunks: List[Dict],
        paper_count: int
    ) -> float:
        """Calculate answer confidence score"""
        factors = []

        # 1. Number of source papers (more = higher confidence)
        paper_factor = min(paper_count / 5, 1.0)
        factors.append(("papers", paper_factor, 0.3))

        # 2. Number of citations in answer
        citation_count = len(re.findall(r'\[Paper:', answer))
        citation_factor = min(citation_count / 3, 1.0)
        factors.append(("citations", citation_factor, 0.3))

        # 3. Answer length (too short may indicate insufficient info)
        word_count = len(answer.split())
        if word_count < 30:
            length_factor = word_count / 30
        elif word_count > 300:
            length_factor = 0.9  # Very long answers might be less focused
        else:
            length_factor = 1.0
        factors.append(("length", length_factor, 0.2))

        # 4. Hedging words (reduce confidence)
        hedging_words = ["might", "could", "possibly", "perhaps", "maybe", "unclear", "uncertain"]
        hedging_count = sum(1 for word in hedging_words if word in answer.lower())
        hedging_factor = max(0, 1.0 - hedging_count * 0.15)
        factors.append(("hedging", hedging_factor, 0.2))

        # Calculate weighted confidence
        confidence = sum(factor * weight for _, factor, weight in factors)

        logger.debug(f"Confidence factors: {factors} -> {confidence:.2f}")

        return round(confidence, 2)

    async def multi_hop_qa(
        self,
        question: str,
        initial_chunks: List[Dict],
        search_fn=None,
        max_hops: int = 2
    ) -> QAResult:
        """
        Multi-hop QA that can retrieve additional context

        Args:
            question: User's question
            initial_chunks: Initial retrieved chunks
            search_fn: Function to retrieve more chunks
            max_hops: Maximum number of retrieval hops

        Returns:
            QAResult
        """
        all_chunks = initial_chunks.copy()
        current_answer = None

        for hop in range(max_hops):
            # Answer with current chunks
            result = await self.answer_question(question, all_chunks)

            # Check if we need more information
            if result.confidence > 0.7 or not search_fn:
                return result

            # Extract entities from current answer for next retrieval
            if self.llm_available and hop < max_hops - 1:
                # Get follow-up queries
                follow_up = await self._generate_follow_up_query(question, result.answer)

                if follow_up and search_fn:
                    # Retrieve more chunks
                    additional_chunks = await search_fn(follow_up, top_k=10)
                    all_chunks.extend(additional_chunks)

            current_answer = result

        return current_answer or result

    async def _generate_follow_up_query(
        self,
        original_question: str,
        partial_answer: str
    ) -> Optional[str]:
        """Generate follow-up query to get more information"""
        if not self.llm_available:
            return None

        prompt = f"""Given this question and partial answer, generate a follow-up search query to find missing information.

Question: {original_question}
Partial Answer: {partial_answer}

Follow-up query (or "NONE" if sufficient):"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )

            follow_up = response.choices[0].message.content.strip()

            if follow_up.upper() == "NONE" or not follow_up:
                return None

            return follow_up

        except Exception as e:
            logger.error(f"Follow-up query generation failed: {e}")
            return None

# Semantic Search & QA Module - 설계 문서

**모듈명:** Semantic Search & Question Answering
**버전:** 1.0
**작성일:** 2025-11-14
**담당:** Search & Intelligence Team

---

## 1. 모듈 개요

### 1.1 목적
자연어 질의를 통한 논문 검색 및 구체적인 연구 질문에 대한 답변 생성

### 1.2 핵심 기능
- 다중 모드 검색 (Vector, Graph, Hybrid)
- 자연어 질의응답
- 인용 기반 답변 생성
- 비교 분석 (논문/기법 비교)
- 트렌드 분석

---

## 2. 검색 모드

### 2.1 Search Modes

```python
from enum import Enum

class SearchMode(str, Enum):
    VECTOR = "vector"        # 순수 벡터 유사도
    GRAPH = "graph"          # 지식 그래프 기반
    HYBRID = "hybrid"        # Vector + Graph
    QA = "qa"               # 질문 답변
    COMPARISON = "comparison"  # 비교 분석

class SearchService:
    """통합 검색 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.vector_search = VectorSearchService(db)
        self.graph_query = GraphQueryService(db)
        self.qa_engine = QAEngine(db)

    async def search(
        self,
        query: str,
        mode: SearchMode = SearchMode.HYBRID,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> SearchResult:
        """통합 검색"""

        # Query 분석
        query_analysis = await self._analyze_query(query)

        if mode == SearchMode.VECTOR:
            return await self._vector_search(query, top_k, filters)
        elif mode == SearchMode.GRAPH:
            return await self._graph_search(query_analysis, top_k)
        elif mode == SearchMode.HYBRID:
            return await self._hybrid_search(query, query_analysis, top_k, filters)
        elif mode == SearchMode.QA:
            return await self._qa_search(query, query_analysis)
        elif mode == SearchMode.COMPARISON:
            return await self._comparison_search(query_analysis)

    async def _analyze_query(self, query: str) -> QueryAnalysis:
        """쿼리 의도 분석"""
        from openai import OpenAI

        client = OpenAI()

        prompt = f"""Analyze this research query:
        Query: {query}

        Extract:
        1. Main topic/concept
        2. Intent (find_papers, compare, explain, trend_analysis)
        3. Time constraints (recent, specific year)
        4. Entities mentioned

        Respond in JSON format.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        import json
        analysis = json.loads(response.choices[0].message.content)

        return QueryAnalysis(
            main_topic=analysis.get("main_topic"),
            intent=analysis.get("intent"),
            time_constraint=analysis.get("time_constraint"),
            entities=analysis.get("entities", [])
        )

    async def _hybrid_search(
        self,
        query: str,
        analysis: QueryAnalysis,
        top_k: int,
        filters: Optional[Dict]
    ) -> SearchResult:
        """하이브리드 검색"""

        # 1. Vector search
        vector_results = await self.vector_search.search_papers(
            query,
            top_k=top_k * 2,
            search_type="hybrid"
        )

        # 2. Graph-based expansion
        if analysis.main_topic:
            graph_results = await self.graph_query.find_related_papers(
                analysis.main_topic,
                max_depth=2
            )
        else:
            graph_results = []

        # 3. Combine with RRF
        combined = self._reciprocal_rank_fusion(
            [vector_results, graph_results],
            weights=[0.7, 0.3]
        )

        # 4. Apply filters
        if filters:
            combined = self._apply_filters(combined, filters)

        # 5. Generate summary
        summary = await self._generate_search_summary(query, combined[:top_k])

        return SearchResult(
            papers=combined[:top_k],
            summary=summary,
            related_concepts=graph_results.get("concepts", []),
            total_count=len(combined)
        )
```

---

## 3. 질의응답 엔진

### 3.1 QA Engine

```python
class QAEngine:
    """질의응답 엔진"""

    def __init__(self, db: Session):
        self.db = db
        self.vector_search = VectorSearchService(db)
        self.llm = ChatOpenAI(model="gpt-4o-mini")

    async def answer_question(
        self,
        question: str,
        max_context_papers: int = 5
    ) -> QAResult:
        """질문에 답변"""

        # 1. Retrieve relevant chunks
        relevant_chunks = await self.vector_search.search_chunks(
            question,
            top_k=20
        )

        # 2. Build context from top papers
        context_parts = []
        paper_ids = set()

        for chunk in relevant_chunks[:max_context_papers * 4]:
            if chunk["paper_id"] not in paper_ids:
                paper_ids.add(chunk["paper_id"])

            context_parts.append(
                f"[Paper: {chunk['paper_title']}]\n{chunk['chunk_text']}\n"
            )

        context = "\n\n".join(context_parts)

        # 3. Generate answer with citations
        prompt = f"""Based on the following research papers, answer the question.
        Provide specific citations to papers using [Paper: title] format.

        Context:
        {context}

        Question: {question}

        Answer (with citations):"""

        response = self.llm.invoke(prompt)

        # 4. Extract citations
        citations = self._extract_citations(response, relevant_chunks)

        # 5. Calculate confidence
        confidence = self._calculate_confidence(
            response,
            relevant_chunks,
            len(paper_ids)
        )

        return QAResult(
            question=question,
            answer=response,
            citations=citations,
            source_papers=list(paper_ids),
            confidence=confidence,
            context_chunks=len(context_parts)
        )

    def _extract_citations(
        self,
        answer: str,
        chunks: List[Dict]
    ) -> List[Citation]:
        """답변에서 인용 추출"""
        import re

        citations = []
        citation_pattern = r'\[Paper: ([^\]]+)\]'

        matches = re.findall(citation_pattern, answer)

        for title in matches:
            # Find matching chunk
            chunk = next(
                (c for c in chunks if title in c["paper_title"]),
                None
            )

            if chunk:
                citations.append(Citation(
                    paper_id=chunk["paper_id"],
                    paper_title=chunk["paper_title"],
                    snippet=chunk["chunk_text"][:200]
                ))

        return citations

    def _calculate_confidence(
        self,
        answer: str,
        chunks: List[Dict],
        paper_count: int
    ) -> float:
        """답변 신뢰도 계산"""

        # Factors:
        # 1. Number of source papers (more = higher confidence)
        paper_factor = min(paper_count / 5, 1.0)

        # 2. Number of citations in answer
        citation_count = len(re.findall(r'\[Paper:', answer))
        citation_factor = min(citation_count / 3, 1.0)

        # 3. Answer length (too short = low confidence)
        word_count = len(answer.split())
        length_factor = min(word_count / 100, 1.0)

        # 4. Hedging words (might, could, possibly = lower confidence)
        hedging_words = ["might", "could", "possibly", "perhaps", "maybe"]
        hedging_count = sum(1 for word in hedging_words if word in answer.lower())
        hedging_factor = max(0, 1.0 - hedging_count * 0.1)

        confidence = (
            paper_factor * 0.3 +
            citation_factor * 0.3 +
            length_factor * 0.2 +
            hedging_factor * 0.2
        )

        return confidence
```

---

## 4. 비교 분석

### 4.1 Comparison Engine

```python
class ComparisonEngine:
    """논문/기법 비교"""

    def __init__(self, db: Session):
        self.db = db
        self.llm = ChatOpenAI(model="gpt-4o-mini")

    async def compare(
        self,
        entities: List[str],
        aspects: List[str] = ["approach", "performance", "limitations"]
    ) -> ComparisonResult:
        """엔티티 비교"""

        # 1. Retrieve papers/info for each entity
        entity_contexts = {}
        for entity in entities:
            papers = await self._find_entity_papers(entity)
            entity_contexts[entity] = self._build_entity_context(papers)

        # 2. Generate comparison
        prompt = self._build_comparison_prompt(
            entities,
            entity_contexts,
            aspects
        )

        response = self.llm.invoke(prompt)

        # 3. Parse comparison table
        comparison_table = self._parse_comparison(response, entities, aspects)

        return ComparisonResult(
            entities=entities,
            aspects=aspects,
            comparison_table=comparison_table,
            summary=response
        )

    def _build_comparison_prompt(
        self,
        entities: List[str],
        contexts: Dict[str, str],
        aspects: List[str]
    ) -> str:
        """비교 프롬프트 생성"""

        context_str = "\n\n".join([
            f"## {entity}\n{context}"
            for entity, context in contexts.items()
        ])

        return f"""Compare the following entities across specified aspects:

        Entities: {', '.join(entities)}
        Aspects: {', '.join(aspects)}

        Context:
        {context_str}

        Provide a detailed comparison in table format, then summarize key differences.
        """
```

---

## 5. 트렌드 분석

### 5.1 Trend Analyzer

```python
class TrendAnalyzer:
    """연구 트렌드 분석"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_temporal_trend(
        self,
        concept: str,
        start_year: int,
        end_year: int
    ) -> TrendAnalysis:
        """시간에 따른 트렌드 분석"""

        # 연도별 논문 수
        yearly_counts = self.db.execute(f"""
            SELECT
                EXTRACT(YEAR FROM published_at) as year,
                COUNT(*) as count
            FROM papers p
            JOIN kg_entity_papers ep ON p.id = ep.paper_id
            JOIN kg_entities e ON ep.entity_id = e.id
            WHERE e.entity_name = :concept
                AND EXTRACT(YEAR FROM published_at) BETWEEN :start AND :end
            GROUP BY year
            ORDER BY year
        """, {"concept": concept, "start": start_year, "end": end_year}).fetchall()

        # 관련 개념 변화
        related_concepts = self._analyze_concept_evolution(concept, start_year, end_year)

        # 성장률 계산
        growth_rate = self._calculate_growth_rate([c[1] for c in yearly_counts])

        return TrendAnalysis(
            concept=concept,
            yearly_counts=dict(yearly_counts),
            related_concepts=related_concepts,
            growth_rate=growth_rate,
            trend_direction="increasing" if growth_rate > 0 else "decreasing"
        )

    def _calculate_growth_rate(self, counts: List[int]) -> float:
        """연평균 성장률"""
        if len(counts) < 2:
            return 0.0

        first_year = counts[0]
        last_year = counts[-1]
        years = len(counts) - 1

        if first_year == 0:
            return 0.0

        growth = ((last_year / first_year) ** (1 / years)) - 1
        return growth
```

---

## 6. API 엔드포인트

```python
@router.post("/search")
async def search_papers(
    query: str,
    mode: SearchMode = SearchMode.HYBRID,
    top_k: int = 10,
    filters: Optional[Dict] = None,
    db: Session = Depends(get_db)
):
    """논문 검색"""
    service = SearchService(db)
    result = await service.search(query, mode, top_k, filters)
    return result

@router.post("/qa")
async def answer_question(
    question: str,
    db: Session = Depends(get_db)
):
    """질의응답"""
    qa_engine = QAEngine(db)
    result = await qa_engine.answer_question(question)
    return result

@router.post("/compare")
async def compare_entities(
    entities: List[str],
    aspects: List[str] = ["approach", "performance"],
    db: Session = Depends(get_db)
):
    """비교 분석"""
    comparison = ComparisonEngine(db)
    result = await comparison.compare(entities, aspects)
    return result

@router.get("/trends/{concept}")
async def analyze_trend(
    concept: str,
    start_year: int = 2020,
    end_year: int = 2025,
    db: Session = Depends(get_db)
):
    """트렌드 분석"""
    analyzer = TrendAnalyzer(db)
    result = analyzer.analyze_temporal_trend(concept, start_year, end_year)
    return result
```

---

## 7. 데이터 모델

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class QueryAnalysis(BaseModel):
    main_topic: str
    intent: str
    time_constraint: Optional[str]
    entities: List[str]

class SearchResult(BaseModel):
    papers: List[Dict]
    summary: str
    related_concepts: List[str]
    total_count: int

class Citation(BaseModel):
    paper_id: str
    paper_title: str
    snippet: str

class QAResult(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    source_papers: List[str]
    confidence: float
    context_chunks: int

class ComparisonResult(BaseModel):
    entities: List[str]
    aspects: List[str]
    comparison_table: Dict
    summary: str

class TrendAnalysis(BaseModel):
    concept: str
    yearly_counts: Dict[int, int]
    related_concepts: List[str]
    growth_rate: float
    trend_direction: str
```

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14

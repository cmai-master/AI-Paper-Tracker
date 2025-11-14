# Knowledge Graph Module - 설계 문서

**모듈명:** Knowledge Graph (LightRAG)
**버전:** 1.0
**작성일:** 2025-11-14
**담당:** Knowledge Engineering Team

---

## 1. 모듈 개요

### 1.1 목적
논문 간의 관계, 연구 개념, 기술 발전 경로를 그래프 구조로 표현하여 컨텍스트 인식 검색 및 인사이트 도출

### 1.2 핵심 책임
- 논문에서 엔티티 및 관계 자동 추출
- 지식 그래프 구축 및 유지보수
- 그래프 기반 쿼리 및 추론
- 연구 트렌드 및 경로 분석
- 개념 간 연결 시각화

### 1.3 주요 기능
1. **Entity Extraction**: 논문에서 개념, 기술, 저자, 데이터셋 추출
2. **Relationship Extraction**: 엔티티 간 관계 식별
3. **Graph Storage**: Neo4j 또는 PostgreSQL 기반 그래프 저장
4. **LightRAG Integration**: 그래프 기반 RAG 쿼리
5. **Temporal Analysis**: 시간에 따른 연구 발전 추적
6. **Community Detection**: 연구 커뮤니티 및 클러스터 발견

---

## 2. 아키텍처

### 2.1 시스템 구조

```
┌─────────────────────────────────────────────────────────┐
│            Knowledge Graph Module                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │        Entity & Relationship Extraction            │ │
│  │                                                     │ │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────┐   │ │
│  │  │   NER    │  │ Relation  │  │   Pattern    │   │ │
│  │  │ (SpaCy/  │  │ Extractor │  │   Matcher    │   │ │
│  │  │ LLM)     │  │   (LLM)   │  │              │   │ │
│  │  └────┬─────┘  └─────┬─────┘  └──────┬───────┘   │ │
│  │       └──────────────┼────────────────┘           │ │
│  └──────────────────────┼────────────────────────────┘ │
│                         │                               │
│  ┌──────────────────────▼────────────────────────────┐ │
│  │            LightRAG Integration                    │ │
│  │                                                     │ │
│  │  ┌─────────────────────────────────────────────┐  │ │
│  │  │ LightRAG Core                                │  │ │
│  │  │ - Entity normalization                       │  │ │
│  │  │ - Relationship weighting                     │  │ │
│  │  │ - Graph construction                         │  │ │
│  │  └───────────────────┬─────────────────────────┘  │ │
│  └────────────────────────┼──────────────────────────┘ │
│                           │                             │
│  ┌────────────────────────▼──────────────────────────┐ │
│  │           Graph Storage Layer                     │ │
│  │                                                    │ │
│  │  ┌──────────────┐         ┌──────────────┐       │ │
│  │  │  PostgreSQL  │   OR    │    Neo4j     │       │ │
│  │  │  (networkx   │         │  (Native     │       │ │
│  │  │   + tables)  │         │   Graph DB)  │       │ │
│  │  └──────────────┘         └──────────────┘       │ │
│  └───────────────────────────────────────────────────┘ │
│                           │                             │
│  ┌────────────────────────▼──────────────────────────┐ │
│  │         Query & Analysis Layer                    │ │
│  │                                                    │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │ │
│  │  │ Graph    │  │Community │  │  Trajectory  │   │ │
│  │  │ Query    │  │Detection │  │   Analysis   │   │ │
│  │  └──────────┘  └──────────┘  └──────────────┘   │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.2 그래프 스키마

```
Nodes (Entities):
┌──────────────┐
│    Paper     │  - arxiv_id, title, year
└──────────────┘

┌──────────────┐
│   Concept    │  - name, type (technique/architecture/task)
└──────────────┘

┌──────────────┐
│    Author    │  - name, affiliation
└──────────────┘

┌──────────────┐
│   Dataset    │  - name, domain, size
└──────────────┘

┌──────────────┐
│  Methodology │  - name, description
└──────────────┘

Relationships:
Paper -[CITES]-> Paper
Paper -[INTRODUCES]-> Concept
Paper -[USES]-> Dataset
Paper -[APPLIES]-> Methodology
Paper -[AUTHORED_BY]-> Author
Concept -[BUILDS_ON]-> Concept
Concept -[IMPROVES]-> Concept
Concept -[RELATED_TO]-> Concept
Author -[COLLABORATES_WITH]-> Author
```

---

## 3. 데이터 모델

### 3.1 데이터베이스 스키마 (PostgreSQL 기반)

```sql
-- 엔티티 테이블
CREATE TABLE kg_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Entity Info
    entity_type VARCHAR(50) NOT NULL,  -- paper, concept, author, dataset, methodology
    entity_id VARCHAR(200) NOT NULL,  -- Normalized identifier
    entity_name TEXT NOT NULL,

    -- Metadata (JSONB for flexibility)
    properties JSONB,

    -- Temporal
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT NOW(),

    -- Stats
    occurrence_count INT DEFAULT 1,
    importance_score FLOAT DEFAULT 0.0,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_entity UNIQUE (entity_type, entity_id)
);

-- 관계 테이블
CREATE TABLE kg_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationship
    source_entity_id UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,  -- CITES, INTRODUCES, etc.

    -- Weight & Confidence
    weight FLOAT DEFAULT 1.0,
    confidence FLOAT DEFAULT 1.0,

    -- Context
    context TEXT,  -- Where this relationship was found
    paper_id UUID REFERENCES papers(id),

    -- Temporal
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_relationship UNIQUE (source_entity_id, target_entity_id, relationship_type)
);

-- 엔티티-논문 매핑
CREATE TABLE kg_entity_papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,

    -- Mention count in this paper
    mention_count INT DEFAULT 1,

    -- Section where mentioned
    sections TEXT[],

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_entity_paper UNIQUE (entity_id, paper_id)
);

-- 그래프 커뮤니티 (Clustering)
CREATE TABLE kg_communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    community_name VARCHAR(200),
    entity_ids UUID[],  -- Member entities

    -- Characteristics
    size INT,
    density FLOAT,
    central_concepts TEXT[],

    -- Temporal
    time_period_start DATE,
    time_period_end DATE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_entities_type ON kg_entities(entity_type);
CREATE INDEX idx_entities_name ON kg_entities(entity_name);
CREATE INDEX idx_entities_importance ON kg_entities(importance_score DESC);
CREATE INDEX idx_relationships_source ON kg_relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON kg_relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON kg_relationships(relationship_type);
CREATE INDEX idx_entity_papers_entity ON kg_entity_papers(entity_id);
CREATE INDEX idx_entity_papers_paper ON kg_entity_papers(paper_id);
CREATE INDEX idx_entities_props ON kg_entities USING gin(properties);
```

### 3.2 내부 데이터 모델

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set
from datetime import datetime
from enum import Enum

class EntityType(str, Enum):
    PAPER = "paper"
    CONCEPT = "concept"
    AUTHOR = "author"
    DATASET = "dataset"
    METHODOLOGY = "methodology"
    TASK = "task"
    METRIC = "metric"

class RelationType(str, Enum):
    CITES = "CITES"
    INTRODUCES = "INTRODUCES"
    USES = "USES"
    APPLIES = "APPLIES"
    IMPROVES = "IMPROVES"
    BUILDS_ON = "BUILDS_ON"
    RELATED_TO = "RELATED_TO"
    AUTHORED_BY = "AUTHORED_BY"
    COLLABORATES_WITH = "COLLABORATES_WITH"
    EVALUATED_ON = "EVALUATED_ON"

class Entity(BaseModel):
    id: str
    entity_type: EntityType
    entity_id: str  # Normalized ID
    entity_name: str
    properties: Dict = Field(default_factory=dict)
    occurrence_count: int = 1
    importance_score: float = 0.0
    first_seen_at: Optional[datetime]
    last_updated_at: datetime

class Relationship(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationType
    weight: float = 1.0
    confidence: float = 1.0
    context: Optional[str]
    paper_id: Optional[str]
    created_at: datetime

class KnowledgeGraph(BaseModel):
    entities: Dict[str, Entity]
    relationships: List[Relationship]

    def add_entity(self, entity: Entity):
        """엔티티 추가 또는 업데이트"""
        if entity.id in self.entities:
            # 기존 엔티티 업데이트
            existing = self.entities[entity.id]
            existing.occurrence_count += 1
            existing.last_updated_at = datetime.utcnow()
        else:
            self.entities[entity.id] = entity

    def add_relationship(self, relationship: Relationship):
        """관계 추가"""
        # 중복 체크
        existing = next(
            (r for r in self.relationships
             if r.source_entity_id == relationship.source_entity_id
             and r.target_entity_id == relationship.target_entity_id
             and r.relationship_type == relationship.relationship_type),
            None
        )

        if existing:
            # 가중치 업데이트
            existing.weight += relationship.weight
        else:
            self.relationships.append(relationship)

class GraphQueryResult(BaseModel):
    """그래프 쿼리 결과"""
    entities: List[Entity]
    relationships: List[Relationship]
    context: str
    confidence: float
```

---

## 4. 엔티티 및 관계 추출

### 4.1 Named Entity Recognition

```python
import spacy
from typing import List, Dict
import re

class EntityExtractor:
    """엔티티 추출기"""

    def __init__(self):
        # Load scientific NER model
        try:
            self.nlp = spacy.load("en_core_sci_lg")  # SciBERT-based
        except:
            self.nlp = spacy.load("en_core_web_lg")

        # Custom patterns for ML/AI entities
        self.ml_patterns = self._load_ml_patterns()

    def extract_entities(self, paper: ProcessedDocument) -> List[Entity]:
        """논문에서 엔티티 추출"""
        entities = []

        # 1. Extract from title and abstract (가장 중요)
        text = f"{paper.title}\n\n{paper.abstract}"
        doc = self.nlp(text)

        # Named entities from spaCy
        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "ORG", "GPE", "TECH"]:
                entities.append(Entity(
                    id=self._normalize_entity_id(ent.text),
                    entity_type=EntityType.CONCEPT,
                    entity_id=self._normalize_entity_id(ent.text),
                    entity_name=ent.text,
                    properties={"label": ent.label_},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        # 2. Pattern-based extraction
        pattern_entities = self._extract_by_patterns(text)
        entities.extend(pattern_entities)

        # 3. Extract datasets
        dataset_entities = self._extract_datasets(text)
        entities.extend(dataset_entities)

        # 4. Extract authors
        author_entities = self._extract_authors(paper)
        entities.extend(author_entities)

        # 5. Extract metrics
        metric_entities = self._extract_metrics(text)
        entities.extend(metric_entities)

        return entities

    def _extract_by_patterns(self, text: str) -> List[Entity]:
        """패턴 기반 추출"""
        entities = []

        for pattern_name, pattern_regex in self.ml_patterns.items():
            matches = re.findall(pattern_regex, text, re.IGNORECASE)

            for match in matches:
                entity_text = match if isinstance(match, str) else match[0]
                entities.append(Entity(
                    id=self._normalize_entity_id(entity_text),
                    entity_type=EntityType.CONCEPT,
                    entity_id=self._normalize_entity_id(entity_text),
                    entity_name=entity_text,
                    properties={"pattern": pattern_name},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        return entities

    def _load_ml_patterns(self) -> Dict[str, str]:
        """ML/AI 관련 패턴"""
        return {
            "architecture": r'\b(?:[A-Z][a-z]+)?(?:Net|Former|GAN|VAE|RNN|LSTM|GRU|CNN|Transformer)\b',
            "technique": r'\b(?:attention|self-attention|cross-attention|multi-head|pooling)\s+(?:mechanism|layer)?\b',
            "algorithm": r'\b(?:gradient\s+descent|backpropagation|dropout|batch\s+normalization|layer\s+normalization)\b',
            "optimization": r'\b(?:Adam|SGD|RMSprop|AdaGrad|LAMB)\s+optimizer\b',
            "loss": r'\b(?:cross-entropy|MSE|MAE|contrastive|triplet)\s+loss\b',
        }

    def _extract_datasets(self, text: str) -> List[Entity]:
        """데이터셋 추출"""
        # 잘 알려진 데이터셋
        known_datasets = [
            "ImageNet", "COCO", "MNIST", "CIFAR-10", "CIFAR-100",
            "SQuAD", "GLUE", "SuperGLUE", "WikiText", "Penn Treebank",
            "MS-COCO", "Pascal VOC", "ADE20K", "OpenImages"
        ]

        entities = []
        for dataset in known_datasets:
            if re.search(rf'\b{dataset}\b', text, re.IGNORECASE):
                entities.append(Entity(
                    id=f"dataset_{dataset.lower().replace(' ', '_')}",
                    entity_type=EntityType.DATASET,
                    entity_id=dataset.lower().replace(' ', '_'),
                    entity_name=dataset,
                    properties={},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        return entities

    def _extract_authors(self, paper: ProcessedDocument) -> List[Entity]:
        """저자 추출"""
        entities = []

        for author in paper.authors:
            entities.append(Entity(
                id=f"author_{self._normalize_entity_id(author.name)}",
                entity_type=EntityType.AUTHOR,
                entity_id=self._normalize_entity_id(author.name),
                entity_name=author.name,
                properties={
                    "affiliation": author.affiliation,
                    "email": author.email
                },
                first_seen_at=datetime.utcnow(),
                last_updated_at=datetime.utcnow()
            ))

        return entities

    def _extract_metrics(self, text: str) -> List[Entity]:
        """평가 메트릭 추출"""
        known_metrics = [
            "accuracy", "precision", "recall", "F1 score", "BLEU",
            "ROUGE", "perplexity", "AUC", "mAP", "IoU"
        ]

        entities = []
        for metric in known_metrics:
            if re.search(rf'\b{metric}\b', text, re.IGNORECASE):
                entities.append(Entity(
                    id=f"metric_{metric.lower().replace(' ', '_')}",
                    entity_type=EntityType.METRIC,
                    entity_id=metric.lower().replace(' ', '_'),
                    entity_name=metric,
                    properties={},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        return entities

    def _normalize_entity_id(self, text: str) -> str:
        """엔티티 ID 정규화"""
        # 소문자, 공백 -> underscore
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = re.sub(r'[^\w_]', '', normalized)
        return normalized
```

### 4.2 Relationship Extraction

```python
from openai import OpenAI

class RelationshipExtractor:
    """관계 추출기 (LLM 기반)"""

    def __init__(self):
        self.client = OpenAI()

    def extract_relationships(
        self,
        paper: ProcessedDocument,
        entities: List[Entity]
    ) -> List[Relationship]:
        """엔티티 간 관계 추출"""
        relationships = []

        # 1. Citation relationships
        citation_rels = self._extract_citation_relationships(paper)
        relationships.extend(citation_rels)

        # 2. Concept relationships (LLM-based)
        concept_entities = [e for e in entities if e.entity_type == EntityType.CONCEPT]
        if len(concept_entities) >= 2:
            concept_rels = self._extract_concept_relationships(
                paper,
                concept_entities
            )
            relationships.extend(concept_rels)

        # 3. Author relationships
        author_entities = [e for e in entities if e.entity_type == EntityType.AUTHOR]
        if len(author_entities) >= 2:
            author_rels = self._extract_author_relationships(author_entities)
            relationships.extend(author_rels)

        # 4. Paper-Dataset relationships
        dataset_entities = [e for e in entities if e.entity_type == EntityType.DATASET]
        for dataset_entity in dataset_entities:
            relationships.append(Relationship(
                source_entity_id=f"paper_{paper.paper_id}",
                target_entity_id=dataset_entity.id,
                relationship_type=RelationType.EVALUATED_ON,
                weight=1.0,
                confidence=0.9,
                paper_id=paper.paper_id,
                created_at=datetime.utcnow()
            ))

        return relationships

    def _extract_citation_relationships(
        self,
        paper: ProcessedDocument
    ) -> List[Relationship]:
        """인용 관계 추출"""
        relationships = []

        for reference in paper.references:
            if reference.linked_paper_id:
                relationships.append(Relationship(
                    source_entity_id=f"paper_{paper.paper_id}",
                    target_entity_id=f"paper_{reference.linked_paper_id}",
                    relationship_type=RelationType.CITES,
                    weight=1.0,
                    confidence=1.0,
                    paper_id=paper.paper_id,
                    created_at=datetime.utcnow()
                ))

        return relationships

    def _extract_concept_relationships(
        self,
        paper: ProcessedDocument,
        concepts: List[Entity]
    ) -> List[Relationship]:
        """개념 간 관계 추출 (LLM 사용)"""

        # LLM에 요청
        concept_names = [c.entity_name for c in concepts[:10]]  # 최대 10개

        prompt = f"""Given a research paper abstract and a list of concepts,
        identify relationships between these concepts.

        Abstract: {paper.abstract[:500]}

        Concepts: {', '.join(concept_names)}

        For each pair of related concepts, specify the relationship type:
        - IMPROVES: concept A improves concept B
        - BUILDS_ON: concept A builds on concept B
        - RELATED_TO: concepts are related but no clear dependency

        Respond in JSON format:
        [{{"source": "concept1", "target": "concept2", "type": "IMPROVES", "confidence": 0.9}}, ...]
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        try:
            import json
            result = json.loads(response.choices[0].message.content)
            relationships = []

            for rel_data in result.get("relationships", []):
                source_concept = next(
                    (c for c in concepts if c.entity_name == rel_data["source"]),
                    None
                )
                target_concept = next(
                    (c for c in concepts if c.entity_name == rel_data["target"]),
                    None
                )

                if source_concept and target_concept:
                    relationships.append(Relationship(
                        source_entity_id=source_concept.id,
                        target_entity_id=target_concept.id,
                        relationship_type=RelationType(rel_data["type"]),
                        weight=1.0,
                        confidence=rel_data.get("confidence", 0.7),
                        context=paper.abstract[:200],
                        paper_id=paper.paper_id,
                        created_at=datetime.utcnow()
                    ))

            return relationships

        except Exception as e:
            logger.error(f"LLM relationship extraction failed: {e}")
            return []

    def _extract_author_relationships(
        self,
        authors: List[Entity]
    ) -> List[Relationship]:
        """저자 간 협력 관계"""
        relationships = []

        # 같은 논문의 저자들은 서로 협력 관계
        for i, author1 in enumerate(authors):
            for author2 in authors[i+1:]:
                relationships.append(Relationship(
                    source_entity_id=author1.id,
                    target_entity_id=author2.id,
                    relationship_type=RelationType.COLLABORATES_WITH,
                    weight=1.0,
                    confidence=1.0,
                    created_at=datetime.utcnow()
                ))

        return relationships
```

---

## 5. LightRAG 통합

### 5.1 LightRAG Wrapper

```python
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache, openai_embedding

class PaperLightRAG:
    """LightRAG 래퍼"""

    def __init__(self, working_dir: str = "./paper_kg"):
        self.rag = LightRAG(
            working_dir=working_dir,
            llm_model_func=self._llm_func,
            embedding_func=self._embedding_func
        )

    async def _llm_func(self, prompt, **kwargs):
        """LLM 함수"""
        return await openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            **kwargs
        )

    async def _embedding_func(self, texts):
        """임베딩 함수"""
        return await openai_embedding(
            texts,
            model="text-embedding-3-small"
        )

    def insert_paper(self, paper: ProcessedDocument):
        """논문을 그래프에 삽입"""
        # 논문 전체 컨텍스트 준비
        context = self._prepare_paper_context(paper)

        # LightRAG에 삽입 (자동으로 엔티티/관계 추출)
        self.rag.insert(context)

    def _prepare_paper_context(self, paper: ProcessedDocument) -> str:
        """논문 컨텍스트 준비"""
        parts = [
            f"Title: {paper.title}",
            f"Authors: {', '.join([a.name for a in paper.authors])}",
            f"Published: {paper.published_at.year}",
            f"\nAbstract:\n{paper.abstract}",
        ]

        # 주요 섹션 추가
        if paper.sections:
            intro = next(
                (s for s in paper.sections if s.section_type == SectionType.INTRODUCTION),
                None
            )
            if intro:
                parts.append(f"\nIntroduction:\n{intro.content[:1000]}")

            method = next(
                (s for s in paper.sections if s.section_type == SectionType.METHODOLOGY),
                None
            )
            if method:
                parts.append(f"\nMethodology:\n{method.content[:1000]}")

            conclusion = next(
                (s for s in paper.sections if s.section_type == SectionType.CONCLUSION),
                None
            )
            if conclusion:
                parts.append(f"\nConclusion:\n{conclusion.content[:500]}")

        return "\n\n".join(parts)

    def query_related_concepts(self, concept: str, mode: str = "hybrid") -> str:
        """개념 관련 논문 및 개념 조회"""
        query = f"What papers and concepts are related to {concept}? Explain the relationships and key findings."

        return self.rag.query(
            query,
            param=QueryParam(mode=mode)
        )

    def trace_research_evolution(self, topic: str) -> str:
        """연구 발전 과정 추적"""
        query = f"Trace the evolution of research on {topic} chronologically. Highlight key papers and breakthroughs."

        return self.rag.query(
            query,
            param=QueryParam(mode="global")  # Global reasoning
        )

    def find_research_gaps(self, domain: str) -> str:
        """연구 갭 식별"""
        query = f"Based on the papers in {domain}, what are the unexplored areas or research gaps? What questions remain unanswered?"

        return self.rag.query(
            query,
            param=QueryParam(mode="global")
        )
```

---

## 6. 그래프 쿼리 및 분석

### 6.1 Graph Query Service

```python
import networkx as nx
from typing import List, Dict, Set

class GraphQueryService:
    """그래프 쿼리 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def build_networkx_graph(self) -> nx.DiGraph:
        """NetworkX 그래프 구축"""
        G = nx.DiGraph()

        # Load entities
        entities = self.db.query(KGEntity).all()
        for entity in entities:
            G.add_node(
                entity.id,
                type=entity.entity_type,
                name=entity.entity_name,
                importance=entity.importance_score
            )

        # Load relationships
        relationships = self.db.query(KGRelationship).all()
        for rel in relationships:
            G.add_edge(
                rel.source_entity_id,
                rel.target_entity_id,
                type=rel.relationship_type,
                weight=rel.weight
            )

        return G

    def find_connected_concepts(
        self,
        concept_id: str,
        max_depth: int = 2
    ) -> List[Entity]:
        """연결된 개념 찾기"""
        G = self.build_networkx_graph()

        if concept_id not in G:
            return []

        # BFS로 탐색
        connected = nx.single_source_shortest_path_length(
            G,
            concept_id,
            cutoff=max_depth
        )

        # 엔티티 정보 가져오기
        entity_ids = list(connected.keys())
        entities = self.db.query(KGEntity).filter(
            KGEntity.id.in_(entity_ids)
        ).all()

        return entities

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str
    ) -> List[str]:
        """최단 경로 찾기"""
        G = self.build_networkx_graph()

        try:
            path = nx.shortest_path(G, source_id, target_id)
            return path
        except nx.NetworkXNoPath:
            return []

    def compute_centrality(self) -> Dict[str, float]:
        """중심성 계산 (중요한 개념 식별)"""
        G = self.build_networkx_graph()

        # PageRank 중심성
        centrality = nx.pagerank(G, weight='weight')

        # DB에 저장
        for entity_id, score in centrality.items():
            self.db.query(KGEntity).filter(
                KGEntity.id == entity_id
            ).update({"importance_score": score})

        self.db.commit()

        return centrality

    def detect_communities(self) -> List[Set[str]]:
        """커뮤니티 감지 (연구 클러스터)"""
        G = self.build_networkx_graph().to_undirected()

        # Louvain 알고리즘
        import community as community_louvain

        partition = community_louvain.best_partition(G)

        # 커뮤니티별로 그룹화
        communities = {}
        for node, comm_id in partition.items():
            if comm_id not in communities:
                communities[comm_id] = set()
            communities[comm_id].add(node)

        return list(communities.values())
```

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14

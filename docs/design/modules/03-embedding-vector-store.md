# Embedding & Vector Store Module - 설계 문서

**모듈명:** Embedding & Vector Store
**버전:** 1.0
**작성일:** 2025-11-14
**담당:** Search & Retrieval Team

---

## 1. 모듈 개요

### 1.1 목적
논문 텍스트를 고차원 벡터로 변환하고 효율적인 유사도 검색을 위해 벡터 데이터베이스에 저장

### 1.2 핵심 책임
- 다중 레벨 임베딩 생성 (문서, 섹션, 청크, 엔티티)
- Dense 및 Sparse 벡터 생성 (하이브리드 검색)
- 벡터 저장 및 인덱싱 (pgvector)
- 고속 ANN(Approximate Nearest Neighbor) 검색
- 임베딩 버전 관리 및 재생성
- 검색 성능 최적화

### 1.3 주요 기능
1. **Multi-Level Embedding**: 다양한 granularity의 임베딩
2. **Hybrid Vectors**: Dense + Sparse 동시 생성
3. **Efficient Storage**: pgvector HNSW 인덱스
4. **Semantic Chunking**: 의미 기반 텍스트 분할
5. **Embedding Cache**: 중복 생성 방지
6. **Model Versioning**: 모델 업그레이드 관리

---

## 2. 아키텍처

### 2.1 시스템 구조

```
┌─────────────────────────────────────────────────────────┐
│          Embedding & Vector Store Module                │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Embedding Generation Layer               │  │
│  │                                                    │  │
│  │  ┌────────────┐    ┌──────────────┐              │  │
│  │  │  BGE-M3    │    │   OpenAI     │              │  │
│  │  │  (Local)   │    │ text-embed-3 │              │  │
│  │  └─────┬──────┘    └──────┬───────┘              │  │
│  │        │                  │                        │  │
│  │        └──────────┬───────┘                        │  │
│  │                   │                                 │  │
│  │         ┌─────────▼─────────┐                      │  │
│  │         │ Embedding Strategy│                      │  │
│  │         │   Selector        │                      │  │
│  │         └─────────┬─────────┘                      │  │
│  └───────────────────┼──────────────────────────────┘  │
│                      │                                  │
│  ┌───────────────────▼──────────────────────────────┐  │
│  │        Chunking & Processing Layer               │  │
│  │                                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐              │  │
│  │  │   Semantic   │  │   Entity     │              │  │
│  │  │   Chunker    │  │  Extractor   │              │  │
│  │  └──────┬───────┘  └──────┬───────┘              │  │
│  │         │                 │                        │  │
│  │         └────────┬────────┘                        │  │
│  └──────────────────┼─────────────────────────────────┘  │
│                     │                                     │
│  ┌──────────────────▼─────────────────────────────────┐  │
│  │           Vector Storage Layer                     │  │
│  │                                                     │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │         PostgreSQL + pgvector                │ │  │
│  │  │                                               │ │  │
│  │  │  ┌─────────────┐    ┌──────────────┐        │ │  │
│  │  │  │ Document    │    │   Chunk      │        │ │  │
│  │  │  │ Embeddings  │    │  Embeddings  │        │ │  │
│  │  │  │  (HNSW)     │    │   (HNSW)     │        │ │  │
│  │  │  └─────────────┘    └──────────────┘        │ │  │
│  │  │                                               │ │  │
│  │  │  ┌─────────────┐    ┌──────────────┐        │ │  │
│  │  │  │  Section    │    │   Entity     │        │ │  │
│  │  │  │ Embeddings  │    │  Embeddings  │        │ │  │
│  │  │  └─────────────┘    └──────────────┘        │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌───────────────────────────────────────────────────┐   │
│  │           Search & Retrieval Layer                │   │
│  │                                                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │  Dense   │  │  Sparse  │  │ Hybrid   │       │   │
│  │  │  Search  │  │  Search  │  │  Search  │       │   │
│  │  └──────────┘  └──────────┘  └──────────┘       │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름

```
입력: ProcessedDocument
    │
    ▼
┌─────────────────┐
│ Text Extraction │
│ - Full text     │
│ - Sections      │
│ - Entities      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Text Chunking   │
│ - Semantic      │
│ - Size-based    │
│ - Overlap       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embedding Gen   │
│ - Dense vector  │
│ - Sparse vector │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Vector Storage  │
│ - pgvector      │
│ - HNSW index    │
└────────┬────────┘
         │
         ▼
    Ready for Search
```

---

## 3. 데이터 모델

### 3.1 데이터베이스 스키마

```sql
-- 문서 레벨 임베딩
CREATE TABLE paper_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,

    -- Embedding Type
    embedding_type VARCHAR(50) NOT NULL,  -- 'document', 'abstract', 'conclusion'

    -- Dense Vector (1024 dimensions for BGE-M3)
    dense_embedding VECTOR(1024) NOT NULL,

    -- Sparse Vector (저장 방식: JSONB로 {term_id: weight})
    sparse_embedding JSONB,

    -- Metadata
    model_name VARCHAR(100) NOT NULL,  -- 'BAAI/bge-m3', 'openai/text-embedding-3-small'
    model_version VARCHAR(50),
    dimension INT NOT NULL,

    -- Content Hash (재생성 필요 여부 판단)
    content_hash CHAR(64),  -- SHA-256 of source text

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_paper_embedding UNIQUE (paper_id, embedding_type, model_name)
);

-- 청크 레벨 임베딩
CREATE TABLE chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    section_id UUID REFERENCES document_sections(id) ON DELETE SET NULL,

    -- Chunk Info
    chunk_index INT NOT NULL,  -- 문서 내 순서
    chunk_text TEXT NOT NULL,
    chunk_size INT,  -- Character count
    start_offset INT,  -- 문서 내 시작 위치
    end_offset INT,

    -- Vectors
    dense_embedding VECTOR(1024) NOT NULL,
    sparse_embedding JSONB,

    -- Metadata
    model_name VARCHAR(100) NOT NULL,
    content_hash CHAR(64),

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_chunk UNIQUE (paper_id, chunk_index, model_name)
);

-- 섹션 레벨 임베딩
CREATE TABLE section_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID REFERENCES document_sections(id) ON DELETE CASCADE,

    -- Vectors
    dense_embedding VECTOR(1024) NOT NULL,
    sparse_embedding JSONB,

    -- Metadata
    model_name VARCHAR(100) NOT NULL,
    content_hash CHAR(64),

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_section_embedding UNIQUE (section_id, model_name)
);

-- 엔티티 임베딩 (개념, 기술, 방법론 등)
CREATE TABLE entity_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Entity Info
    entity_text VARCHAR(200) NOT NULL,
    entity_type VARCHAR(50),  -- 'technique', 'architecture', 'task', 'dataset'
    normalized_text VARCHAR(200),  -- 정규화된 형태

    -- Vector
    dense_embedding VECTOR(1024) NOT NULL,

    -- Metadata
    model_name VARCHAR(100) NOT NULL,
    occurrence_count INT DEFAULT 1,  -- 등장 횟수

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_entity UNIQUE (normalized_text, model_name)
);

-- 임베딩 생성 작업 추적
CREATE TABLE embedding_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,

    job_type VARCHAR(50) NOT NULL,  -- 'initial', 'regenerate', 'update'
    model_name VARCHAR(100) NOT NULL,

    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    progress FLOAT DEFAULT 0.0,  -- 0.0 - 1.0

    -- Stats
    chunks_processed INT DEFAULT 0,
    total_chunks INT,
    processing_time_ms INT,

    error_message TEXT,

    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW 인덱스 (빠른 ANN 검색)
-- m: 각 노드의 최대 연결 수
-- ef_construction: 인덱스 구축 시 탐색 범위
CREATE INDEX paper_embeddings_dense_idx ON paper_embeddings
USING hnsw (dense_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX chunk_embeddings_dense_idx ON chunk_embeddings
USING hnsw (dense_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX section_embeddings_dense_idx ON section_embeddings
USING hnsw (dense_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX entity_embeddings_dense_idx ON entity_embeddings
USING hnsw (dense_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Sparse 임베딩용 GIN 인덱스
CREATE INDEX paper_embeddings_sparse_idx ON paper_embeddings USING gin(sparse_embedding);
CREATE INDEX chunk_embeddings_sparse_idx ON chunk_embeddings USING gin(sparse_embedding);

-- 기타 인덱스
CREATE INDEX chunk_embeddings_paper_idx ON chunk_embeddings(paper_id);
CREATE INDEX embedding_jobs_status_idx ON embedding_jobs(status);
CREATE INDEX entity_embeddings_text_idx ON entity_embeddings(normalized_text);
```

### 3.2 내부 데이터 모델

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime
from enum import Enum

class EmbeddingModel(str, Enum):
    BGE_M3 = "BAAI/bge-m3"
    BGE_LARGE_EN = "BAAI/bge-large-en-v1.5"
    OPENAI_SMALL = "openai/text-embedding-3-small"
    OPENAI_LARGE = "openai/text-embedding-3-large"

class EmbeddingType(str, Enum):
    DOCUMENT = "document"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    CONCLUSION = "conclusion"
    FULL_TEXT = "full_text"

class VectorType(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"

class DenseVector(BaseModel):
    """Dense 임베딩"""
    values: List[float]
    dimension: int

    @property
    def norm(self) -> float:
        import numpy as np
        return float(np.linalg.norm(self.values))

class SparseVector(BaseModel):
    """Sparse 임베딩 (BM25-like)"""
    indices: List[int]
    values: List[float]
    dimension: int

    def to_dict(self) -> Dict[int, float]:
        return dict(zip(self.indices, self.values))

class HybridVector(BaseModel):
    """Dense + Sparse 조합"""
    dense: DenseVector
    sparse: SparseVector

class EmbeddingResult(BaseModel):
    """임베딩 생성 결과"""
    text: str
    text_hash: str
    dense_vector: DenseVector
    sparse_vector: Optional[SparseVector]
    model_name: EmbeddingModel
    model_version: str
    created_at: datetime

class ChunkMetadata(BaseModel):
    """청크 메타데이터"""
    chunk_index: int
    chunk_text: str
    chunk_size: int
    start_offset: int
    end_offset: int
    section_type: Optional[str]
    page_number: Optional[int]

class ChunkEmbedding(BaseModel):
    """청크 임베딩"""
    chunk_metadata: ChunkMetadata
    embedding: EmbeddingResult

class DocumentEmbeddings(BaseModel):
    """문서 전체 임베딩 세트"""
    paper_id: str

    # Document-level
    document_embedding: Optional[EmbeddingResult]
    abstract_embedding: Optional[EmbeddingResult]
    conclusion_embedding: Optional[EmbeddingResult]

    # Chunk-level
    chunk_embeddings: List[ChunkEmbedding]

    # Section-level
    section_embeddings: Dict[str, EmbeddingResult]

    # Entity-level
    entity_embeddings: Dict[str, EmbeddingResult]

    # Stats
    total_chunks: int
    total_sections: int
    total_entities: int

    model_name: EmbeddingModel
    created_at: datetime
```

---

## 4. 임베딩 생성

### 4.1 BGE-M3 임베딩 생성기

```python
from FlagEmbedding import BGEM3FlagModel
import numpy as np
from typing import List, Dict, Union
import torch

class BGEM3Embedder:
    """BGE-M3 임베딩 생성기 (Dense + Sparse)"""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.model_name = model_name
        self.device = device

        # Load model
        self.model = BGEM3FlagModel(
            model_name,
            use_fp16=use_fp16,
            device=device
        )

        self.dimension = 1024  # BGE-M3 dimension

    def embed_single(self, text: str) -> HybridVector:
        """단일 텍스트 임베딩"""
        result = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,  # ColBERT 벡터는 제외
            max_length=8192  # BGE-M3 max length
        )

        # Dense vector
        dense = DenseVector(
            values=result['dense_vecs'][0].tolist(),
            dimension=self.dimension
        )

        # Sparse vector
        sparse_weights = result['lexical_weights'][0]
        if sparse_weights:
            indices = list(sparse_weights.keys())
            values = list(sparse_weights.values())
            sparse = SparseVector(
                indices=indices,
                values=values,
                dimension=30522  # BERT vocab size
            )
        else:
            sparse = None

        return HybridVector(dense=dense, sparse=sparse)

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[HybridVector]:
        """배치 임베딩"""
        all_vectors = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            result = self.model.encode(
                batch_texts,
                return_dense=True,
                return_sparse=True,
                max_length=8192
            )

            for j in range(len(batch_texts)):
                dense = DenseVector(
                    values=result['dense_vecs'][j].tolist(),
                    dimension=self.dimension
                )

                sparse_weights = result['lexical_weights'][j]
                sparse = SparseVector(
                    indices=list(sparse_weights.keys()),
                    values=list(sparse_weights.values()),
                    dimension=30522
                ) if sparse_weights else None

                all_vectors.append(HybridVector(dense=dense, sparse=sparse))

        return all_vectors

    def compute_similarity(self, vec1: DenseVector, vec2: DenseVector) -> float:
        """코사인 유사도 계산"""
        v1 = np.array(vec1.values)
        v2 = np.array(vec2.values)

        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
```

### 4.2 OpenAI 임베딩 생성기

```python
from openai import OpenAI
from typing import List

class OpenAIEmbedder:
    """OpenAI 임베딩 생성기"""

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: Optional[str] = None
    ):
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key)

        # Dimensions
        self.dimension = 1536 if "small" in model_name else 3072

    def embed_single(self, text: str) -> DenseVector:
        """단일 텍스트 임베딩"""
        response = self.client.embeddings.create(
            input=text,
            model=self.model_name
        )

        vector = response.data[0].embedding

        return DenseVector(
            values=vector,
            dimension=len(vector)
        )

    def embed_batch(self, texts: List[str]) -> List[DenseVector]:
        """배치 임베딩 (최대 2048개)"""
        if len(texts) > 2048:
            # Split into chunks
            all_vectors = []
            for i in range(0, len(texts), 2048):
                batch = texts[i:i + 2048]
                vectors = self._embed_batch_internal(batch)
                all_vectors.extend(vectors)
            return all_vectors
        else:
            return self._embed_batch_internal(texts)

    def _embed_batch_internal(self, texts: List[str]) -> List[DenseVector]:
        """내부 배치 처리"""
        response = self.client.embeddings.create(
            input=texts,
            model=self.model_name
        )

        vectors = []
        for item in response.data:
            vectors.append(DenseVector(
                values=item.embedding,
                dimension=len(item.embedding)
            ))

        return vectors
```

### 4.3 임베딩 전략 선택기

```python
class EmbeddingStrategy:
    """임베딩 전략 선택 및 관리"""

    def __init__(self, default_model: EmbeddingModel = EmbeddingModel.BGE_M3):
        self.default_model = default_model
        self.embedders = {
            EmbeddingModel.BGE_M3: BGEM3Embedder(),
            EmbeddingModel.OPENAI_SMALL: OpenAIEmbedder(model_name="text-embedding-3-small"),
            EmbeddingModel.OPENAI_LARGE: OpenAIEmbedder(model_name="text-embedding-3-large"),
        }

    def select_model(self, text_length: int, require_sparse: bool = False) -> EmbeddingModel:
        """텍스트 길이와 요구사항에 따라 모델 선택"""

        # Sparse 벡터가 필요하면 BGE-M3
        if require_sparse:
            return EmbeddingModel.BGE_M3

        # 긴 텍스트는 BGE-M3 (max 8192 tokens)
        if text_length > 8000:
            return EmbeddingModel.BGE_M3

        # 짧은 텍스트는 OpenAI small (비용 효율적)
        if text_length < 1000:
            return EmbeddingModel.OPENAI_SMALL

        # 중간 길이는 기본 모델
        return self.default_model

    def get_embedder(self, model: EmbeddingModel):
        """임베더 인스턴스 반환"""
        return self.embedders.get(model, self.embedders[self.default_model])
```

---

## 5. 텍스트 청킹

### 5.1 Semantic Chunker

```python
from nltk.tokenize import sent_tokenize
from typing import List
import hashlib

class SemanticChunker:
    """의미 기반 텍스트 청킹"""

    def __init__(
        self,
        chunk_size: int = 512,  # tokens
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str) -> List[ChunkMetadata]:
        """텍스트를 청크로 분할"""
        # 문장 단위로 분할
        sentences = sent_tokenize(text)

        chunks = []
        current_chunk = []
        current_size = 0
        char_offset = 0

        for sentence in sentences:
            sentence_size = len(sentence.split())

            # 청크 크기 초과 시
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # 현재 청크 저장
                chunk_text = " ".join(current_chunk)
                chunks.append(self._create_chunk_metadata(
                    chunk_text,
                    len(chunks),
                    char_offset,
                    char_offset + len(chunk_text)
                ))

                # Overlap 처리: 마지막 N개 문장 유지
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk,
                    self.chunk_overlap
                )

                current_chunk = overlap_sentences + [sentence]
                current_size = sum(len(s.split()) for s in current_chunk)
                char_offset += len(chunk_text) - len(" ".join(overlap_sentences))
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        # 마지막 청크
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text.split()) >= self.min_chunk_size:
                chunks.append(self._create_chunk_metadata(
                    chunk_text,
                    len(chunks),
                    char_offset,
                    char_offset + len(chunk_text)
                ))

        return chunks

    def _create_chunk_metadata(
        self,
        text: str,
        index: int,
        start: int,
        end: int
    ) -> ChunkMetadata:
        """청크 메타데이터 생성"""
        return ChunkMetadata(
            chunk_index=index,
            chunk_text=text,
            chunk_size=len(text),
            start_offset=start,
            end_offset=end,
            section_type=None,
            page_number=None
        )

    def _get_overlap_sentences(self, sentences: List[str], target_words: int) -> List[str]:
        """Overlap용 문장 선택"""
        overlap = []
        word_count = 0

        # 뒤에서부터 선택
        for sentence in reversed(sentences):
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= target_words:
                overlap.insert(0, sentence)
                word_count += sentence_words
            else:
                break

        return overlap

    def chunk_by_section(
        self,
        sections: List[DocumentSection]
    ) -> Dict[str, List[ChunkMetadata]]:
        """섹션별 청킹"""
        section_chunks = {}

        for section in sections:
            chunks = self.chunk_text(section.content)

            # 섹션 정보 추가
            for chunk in chunks:
                chunk.section_type = section.section_type

            section_chunks[section.section_type] = chunks

        return section_chunks
```

### 5.2 Fixed-Size Chunker

```python
class FixedSizeChunker:
    """고정 크기 청킹 (간단하고 빠름)"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str) -> List[ChunkMetadata]:
        """고정 크기로 분할"""
        words = text.split()
        chunks = []
        start_idx = 0

        while start_idx < len(words):
            end_idx = min(start_idx + self.chunk_size, len(words))
            chunk_words = words[start_idx:end_idx]
            chunk_text = " ".join(chunk_words)

            chunks.append(ChunkMetadata(
                chunk_index=len(chunks),
                chunk_text=chunk_text,
                chunk_size=len(chunk_text),
                start_offset=start_idx,
                end_offset=end_idx,
                section_type=None,
                page_number=None
            ))

            # Overlap 적용
            start_idx = end_idx - self.overlap if end_idx < len(words) else end_idx

        return chunks
```

---

## 6. 임베딩 파이프라인

### 6.1 Document Embedding Pipeline

```python
from sqlalchemy.orm import Session
import hashlib

class DocumentEmbeddingPipeline:
    """문서 임베딩 생성 파이프라인"""

    def __init__(
        self,
        db: Session,
        embedder: BGEM3Embedder,
        chunker: SemanticChunker
    ):
        self.db = db
        self.embedder = embedder
        self.chunker = chunker

    def process_document(self, paper_id: str, processed_doc: ProcessedDocument):
        """문서 전체 임베딩 생성"""

        # Create job tracking
        job = EmbeddingJob(
            paper_id=paper_id,
            job_type="initial",
            model_name=self.embedder.model_name,
            status="processing",
            started_at=datetime.utcnow()
        )
        self.db.add(job)
        self.db.commit()

        try:
            # 1. Document-level embedding (전체 요약)
            self._create_document_embedding(paper_id, processed_doc)

            # 2. Abstract embedding
            if processed_doc.abstract:
                self._create_section_embedding(
                    paper_id,
                    EmbeddingType.ABSTRACT,
                    processed_doc.abstract
                )

            # 3. Chunk-level embeddings
            chunks = self.chunker.chunk_text(processed_doc.full_text)
            job.total_chunks = len(chunks)
            self.db.commit()

            for chunk in chunks:
                self._create_chunk_embedding(paper_id, chunk)
                job.chunks_processed += 1
                job.progress = job.chunks_processed / job.total_chunks
                self.db.commit()

            # 4. Section embeddings
            for section in processed_doc.sections:
                if section.word_count > 50:  # 최소 길이
                    self._create_section_embedding_from_section(
                        paper_id,
                        section
                    )

            # Complete job
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.processing_time_ms = int(
                (job.completed_at - job.started_at).total_seconds() * 1000
            )
            self.db.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            self.db.commit()
            raise

    def _create_document_embedding(self, paper_id: str, doc: ProcessedDocument):
        """문서 레벨 임베딩"""
        # 전체 텍스트 요약 생성 (title + abstract + conclusion)
        summary_parts = [doc.title]

        if doc.abstract:
            summary_parts.append(doc.abstract)

        conclusion_section = next(
            (s for s in doc.sections if s.section_type == SectionType.CONCLUSION),
            None
        )
        if conclusion_section:
            summary_parts.append(conclusion_section.content[:500])

        summary_text = "\n\n".join(summary_parts)

        # 임베딩 생성
        vector = self.embedder.embed_single(summary_text)
        content_hash = hashlib.sha256(summary_text.encode()).hexdigest()

        # 저장
        embedding = PaperEmbedding(
            paper_id=paper_id,
            embedding_type=EmbeddingType.DOCUMENT,
            dense_embedding=vector.dense.values,
            sparse_embedding=vector.sparse.to_dict() if vector.sparse else None,
            model_name=self.embedder.model_name,
            dimension=vector.dense.dimension,
            content_hash=content_hash
        )

        self.db.add(embedding)
        self.db.commit()

    def _create_chunk_embedding(self, paper_id: str, chunk: ChunkMetadata):
        """청크 임베딩"""
        vector = self.embedder.embed_single(chunk.chunk_text)
        content_hash = hashlib.sha256(chunk.chunk_text.encode()).hexdigest()

        embedding = ChunkEmbedding(
            paper_id=paper_id,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
            chunk_size=chunk.chunk_size,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            dense_embedding=vector.dense.values,
            sparse_embedding=vector.sparse.to_dict() if vector.sparse else None,
            model_name=self.embedder.model_name,
            content_hash=content_hash
        )

        self.db.add(embedding)
        self.db.commit()
```

---

## 7. 벡터 검색

### 7.1 Vector Search Service

```python
class VectorSearchService:
    """벡터 기반 검색 서비스"""

    def __init__(self, db: Session, embedder: BGEM3Embedder):
        self.db = db
        self.embedder = embedder

    def search_papers(
        self,
        query: str,
        top_k: int = 10,
        search_type: Literal["dense", "sparse", "hybrid"] = "hybrid",
        ef_search: int = 40  # HNSW search parameter
    ) -> List[Dict]:
        """논문 검색"""

        # Query embedding
        query_vector = self.embedder.embed_single(query)

        if search_type == "dense":
            return self._dense_search(query_vector.dense, top_k, ef_search)
        elif search_type == "sparse":
            return self._sparse_search(query_vector.sparse, top_k)
        else:  # hybrid
            return self._hybrid_search(query_vector, top_k, ef_search)

    def _dense_search(
        self,
        query_vector: DenseVector,
        top_k: int,
        ef_search: int
    ) -> List[Dict]:
        """Dense 벡터 검색"""

        # pgvector cosine similarity
        query_str = f"[{','.join(map(str, query_vector.values))}]"

        sql = f"""
        SELECT
            p.id,
            p.title,
            p.abstract,
            pe.dense_embedding <=> '{query_str}'::vector AS distance,
            1 - (pe.dense_embedding <=> '{query_str}'::vector) AS similarity
        FROM papers p
        JOIN paper_embeddings pe ON p.id = pe.paper_id
        WHERE pe.embedding_type = 'document'
        ORDER BY pe.dense_embedding <=> '{query_str}'::vector
        LIMIT {top_k}
        """

        # Set ef_search for HNSW
        self.db.execute(f"SET hnsw.ef_search = {ef_search}")

        results = self.db.execute(sql).fetchall()

        return [
            {
                "paper_id": r[0],
                "title": r[1],
                "abstract": r[2],
                "distance": float(r[3]),
                "similarity": float(r[4])
            }
            for r in results
        ]

    def _hybrid_search(
        self,
        query_vector: HybridVector,
        top_k: int,
        ef_search: int,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ) -> List[Dict]:
        """하이브리드 검색 (Dense + Sparse)"""

        # Dense 검색
        dense_results = self._dense_search(
            query_vector.dense,
            top_k * 2,  # 더 많이 가져와서 병합
            ef_search
        )

        # Sparse 검색 (BM25-like)
        sparse_results = self._sparse_search(
            query_vector.sparse,
            top_k * 2
        )

        # Reciprocal Rank Fusion (RRF)
        fused = self._rrf_fusion(
            [dense_results, sparse_results],
            [dense_weight, sparse_weight],
            k=60
        )

        return fused[:top_k]

    def _rrf_fusion(
        self,
        result_lists: List[List[Dict]],
        weights: List[float],
        k: int = 60
    ) -> List[Dict]:
        """Reciprocal Rank Fusion"""
        scores = {}
        paper_data = {}

        for results, weight in zip(result_lists, weights):
            for rank, result in enumerate(results, 1):
                paper_id = result["paper_id"]
                paper_data[paper_id] = result

                if paper_id not in scores:
                    scores[paper_id] = 0

                scores[paper_id] += weight * (1.0 / (k + rank))

        # 점수 기준 정렬
        sorted_papers = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {**paper_data[paper_id], "rrf_score": score}
            for paper_id, score in sorted_papers
        ]

    def search_chunks(
        self,
        query: str,
        top_k: int = 20,
        ef_search: int = 40
    ) -> List[Dict]:
        """청크 레벨 검색 (더 세밀한 검색)"""

        query_vector = self.embedder.embed_single(query)
        query_str = f"[{','.join(map(str, query_vector.dense.values))}]"

        sql = f"""
        SELECT
            ce.paper_id,
            ce.chunk_text,
            ce.chunk_index,
            p.title,
            1 - (ce.dense_embedding <=> '{query_str}'::vector) AS similarity
        FROM chunk_embeddings ce
        JOIN papers p ON ce.paper_id = p.id
        ORDER BY ce.dense_embedding <=> '{query_str}'::vector
        LIMIT {top_k}
        """

        self.db.execute(f"SET hnsw.ef_search = {ef_search}")
        results = self.db.execute(sql).fetchall()

        return [
            {
                "paper_id": r[0],
                "chunk_text": r[1],
                "chunk_index": r[2],
                "paper_title": r[3],
                "similarity": float(r[4])
            }
            for r in results
        ]
```

---

## 8. API 및 태스크

### 8.1 Celery Task

```python
@app.task(bind=True)
def generate_embeddings(self, paper_id: str):
    """임베딩 생성 태스크"""
    try:
        # Get processed document
        processed_doc = db.query(ProcessedDocument).filter(
            ProcessedDocument.paper_id == paper_id
        ).first()

        if not processed_doc:
            raise ValueError(f"Processed document not found: {paper_id}")

        # Generate embeddings
        pipeline = DocumentEmbeddingPipeline(
            db=db,
            embedder=BGEM3Embedder(),
            chunker=SemanticChunker()
        )

        pipeline.process_document(paper_id, processed_doc)

        return {"status": "success", "paper_id": paper_id}

    except Exception as exc:
        logger.error(f"Embedding generation failed: {exc}")
        raise
```

### 8.2 REST API

```python
@router.post("/embeddings/generate")
async def trigger_embedding_generation(
    paper_id: str,
    background_tasks: BackgroundTasks
):
    """임베딩 생성 트리거"""
    background_tasks.add_task(generate_embeddings, paper_id)
    return {"status": "processing", "paper_id": paper_id}

@router.post("/search")
async def search_papers(
    query: str,
    top_k: int = 10,
    search_type: Literal["dense", "sparse", "hybrid"] = "hybrid",
    db: Session = Depends(get_db)
):
    """논문 검색"""
    embedder = BGEM3Embedder()
    search_service = VectorSearchService(db, embedder)

    results = search_service.search_papers(
        query=query,
        top_k=top_k,
        search_type=search_type
    )

    return {"results": results, "count": len(results)}
```

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14

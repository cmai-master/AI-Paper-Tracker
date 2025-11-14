# Data Ingestion Pipeline Module - 설계 문서

**모듈명:** Data Ingestion Pipeline
**버전:** 1.0
**작성일:** 2025-11-14
**담당:** Data Collection Team

---

## 1. 모듈 개요

### 1.1 목적
다양한 외부 소스(arXiv, Semantic Scholar, Papers with Code, Twitter 등)로부터 AI/LLM 관련 논문 데이터를 자동으로 수집하고 정규화하여 시스템에 저장

### 1.2 핵심 책임
- 외부 API와의 안정적인 연동
- Rate Limiting 및 에러 복구
- 중복 데이터 감지 및 처리
- 메타데이터 정규화 및 검증
- 수집 상태 모니터링 및 체크포인트 관리

### 1.3 주요 기능
1. **Multi-Source Collection**: arXiv, Semantic Scholar, Papers with Code, Twitter
2. **Incremental Sync**: 마지막 수집 시점 이후의 신규 데이터만 수집
3. **Deduplication**: 다중 소스에서 수집된 동일 논문 통합
4. **Error Recovery**: 실패한 수집 작업 재시도 및 Dead Letter Queue
5. **Monitoring**: 수집 진행 상황 및 에러 추적

---

## 2. 아키텍처

### 2.1 컴포넌트 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│          Data Ingestion Pipeline                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Scheduler  │  │  Orchestrator│  │   Monitor    │ │
│  │   (Celery    │→ │  (LangGraph) │→ │  (Prometheus)│ │
│  │    Beat)     │  │              │  │              │ │
│  └──────────────┘  └──────┬───────┘  └──────────────┘ │
│                            │                            │
│              ┌─────────────┼─────────────┐             │
│              │             │             │             │
│         ┌────▼────┐  ┌────▼────┐  ┌────▼────┐        │
│         │ arXiv   │  │Semantic │  │ Papers  │        │
│         │Collector│  │Scholar  │  │w/ Code  │        │
│         └────┬────┘  └────┬────┘  └────┬────┘        │
│              │            │            │             │
│              └────────────┼────────────┘             │
│                           │                          │
│                    ┌──────▼──────┐                   │
│                    │ Normalizer  │                   │
│                    │& Validator  │                   │
│                    └──────┬──────┘                   │
│                           │                          │
│                    ┌──────▼──────┐                   │
│                    │ Deduplicator│                   │
│                    └──────┬──────┘                   │
│                           │                          │
│                    ┌──────▼──────┐                   │
│                    │   Storage   │                   │
│                    │  (Postgres) │                   │
│                    └─────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 LangGraph Workflow

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Optional
from datetime import datetime

class IngestionState(TypedDict):
    """수집 파이프라인 상태"""
    source: str  # "arxiv", "semantic_scholar", "papers_with_code"
    query_params: Dict
    checkpoint: datetime
    raw_papers: List[Dict]
    normalized_papers: List[Dict]
    deduplicated_papers: List[Dict]
    stored_count: int
    errors: List[Dict]
    retry_count: int
    status: str  # "pending", "in_progress", "completed", "failed"

# Graph 정의
workflow = StateGraph(IngestionState)

# Nodes
workflow.add_node("fetch", fetch_from_source)
workflow.add_node("normalize", normalize_metadata)
workflow.add_node("deduplicate", check_duplicates)
workflow.add_node("store", store_papers)
workflow.add_node("handle_error", error_handler)

# Edges
workflow.add_edge("fetch", "normalize")
workflow.add_edge("normalize", "deduplicate")
workflow.add_edge("deduplicate", "store")
workflow.add_edge("store", END)

# Conditional edges for error handling
workflow.add_conditional_edges(
    "fetch",
    lambda state: "handle_error" if state["errors"] else "normalize"
)

app = workflow.compile()
```

---

## 3. 데이터 모델

### 3.1 데이터베이스 스키마

```sql
-- 논문 메타데이터 메인 테이블
CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External IDs
    arxiv_id VARCHAR(20) UNIQUE,
    doi VARCHAR(100),
    semantic_scholar_id VARCHAR(50),

    -- Basic Metadata
    title TEXT NOT NULL,
    abstract TEXT,
    authors JSONB NOT NULL,  -- [{"name": "...", "affiliation": "..."}]

    -- Publication Info
    published_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    version INT DEFAULT 1,

    -- Categories & Keywords
    categories TEXT[],  -- ["cs.AI", "cs.CL"]
    primary_category VARCHAR(20),
    keywords TEXT[],

    -- URLs
    pdf_url TEXT,
    abstract_url TEXT,

    -- Source Tracking
    data_source VARCHAR(50) NOT NULL,  -- "arxiv", "semantic_scholar"
    ingested_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW(),

    -- Status
    processing_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed

    CONSTRAINT valid_processing_status
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- 수집 체크포인트 테이블
CREATE TABLE ingestion_checkpoints (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    last_sync_time TIMESTAMP NOT NULL,
    papers_collected INT DEFAULT 0,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_source_checkpoint UNIQUE (source, last_sync_time)
);

-- 중복 감지 핑거프린트
CREATE TABLE paper_fingerprints (
    id SERIAL PRIMARY KEY,
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,

    -- Hashing fields
    title_hash CHAR(64) NOT NULL,  -- SHA-256
    abstract_hash CHAR(64),
    author_hash CHAR(64),

    -- External ID mapping
    arxiv_id VARCHAR(20),
    doi VARCHAR(100),
    semantic_scholar_id VARCHAR(50),

    -- Tracking
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    occurrence_count INT DEFAULT 1,

    CONSTRAINT unique_arxiv_id UNIQUE (arxiv_id),
    CONSTRAINT unique_doi UNIQUE (doi)
);

-- 수집 실패 로그 (Dead Letter Queue)
CREATE TABLE ingestion_failures (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    external_id VARCHAR(100),
    raw_data JSONB,
    error_type VARCHAR(50),
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 5,
    next_retry_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, retrying, failed, resolved
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX idx_papers_published_at ON papers(published_at DESC);
CREATE INDEX idx_papers_categories ON papers USING GIN(categories);
CREATE INDEX idx_papers_status ON papers(processing_status);
CREATE INDEX idx_fingerprints_title_hash ON paper_fingerprints(title_hash);
CREATE INDEX idx_failures_status ON ingestion_failures(status) WHERE status != 'resolved';
```

### 3.2 내부 데이터 모델

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class DataSource(str, Enum):
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PAPERS_WITH_CODE = "papers_with_code"
    TWITTER = "twitter"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None
    orcid: Optional[str] = None

class RawPaper(BaseModel):
    """외부 소스에서 수집한 원본 데이터"""
    source: DataSource
    external_id: str
    title: str
    abstract: Optional[str]
    authors: List[Author]
    published_at: datetime
    updated_at: Optional[datetime]
    categories: List[str] = []
    pdf_url: Optional[str]
    raw_metadata: Dict = Field(default_factory=dict)

    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @validator('authors')
    def authors_not_empty(cls, v):
        if not v:
            raise ValueError('Authors list cannot be empty')
        return v

class NormalizedPaper(BaseModel):
    """정규화된 논문 데이터"""
    arxiv_id: Optional[str]
    doi: Optional[str]
    semantic_scholar_id: Optional[str]

    title: str
    abstract: Optional[str]
    authors: List[Author]

    published_at: datetime
    updated_at: Optional[datetime]
    version: int = 1

    categories: List[str]
    primary_category: Optional[str]
    keywords: List[str] = []

    pdf_url: Optional[str]
    abstract_url: Optional[str]

    data_source: DataSource
    processing_status: ProcessingStatus = ProcessingStatus.PENDING

    # Fingerprints for deduplication
    title_hash: str
    abstract_hash: Optional[str]
    author_hash: str

    def compute_hashes(self):
        import hashlib

        # Title hash
        self.title_hash = hashlib.sha256(
            self.title.lower().strip().encode()
        ).hexdigest()

        # Abstract hash
        if self.abstract:
            self.abstract_hash = hashlib.sha256(
                self.abstract.lower().strip().encode()
            ).hexdigest()

        # Author hash (sorted author names)
        author_str = "|".join(sorted(a.name.lower() for a in self.authors))
        self.author_hash = hashlib.sha256(
            author_str.encode()
        ).hexdigest()
```

---

## 4. 수집기 구현

### 4.1 arXiv Collector

```python
import arxiv
import time
from typing import List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ArxivCollector:
    """arXiv API 수집기"""

    CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.NE", "stat.ML"]
    RATE_LIMIT_DELAY = 3.0  # seconds
    MAX_RESULTS_PER_QUERY = 100

    def __init__(self):
        self.client = arxiv.Client(
            page_size=self.MAX_RESULTS_PER_QUERY,
            delay_seconds=self.RATE_LIMIT_DELAY,
            num_retries=3
        )

    def collect_since(self, since: datetime) -> List[RawPaper]:
        """특정 시점 이후의 논문 수집"""
        logger.info(f"Collecting arXiv papers since {since}")

        # Build query
        category_query = " OR ".join([f"cat:{cat}" for cat in self.CATEGORIES])
        query = f"({category_query}) AND submittedDate:[{since.strftime('%Y%m%d%H%M%S')} TO *]"

        search = arxiv.Search(
            query=query,
            max_results=1000,  # Will paginate automatically
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        papers = []
        for result in self.client.results(search):
            try:
                paper = self._convert_to_raw_paper(result)
                papers.append(paper)
                logger.debug(f"Collected: {paper.title[:50]}...")
            except Exception as e:
                logger.error(f"Error converting arXiv result: {e}", exc_info=True)
                continue

        logger.info(f"Collected {len(papers)} papers from arXiv")
        return papers

    def _convert_to_raw_paper(self, result: arxiv.Result) -> RawPaper:
        """arXiv Result를 RawPaper로 변환"""
        return RawPaper(
            source=DataSource.ARXIV,
            external_id=result.entry_id.split('/')[-1],
            title=result.title,
            abstract=result.summary,
            authors=[
                Author(name=author.name)
                for author in result.authors
            ],
            published_at=result.published,
            updated_at=result.updated,
            categories=result.categories,
            pdf_url=result.pdf_url,
            raw_metadata={
                "entry_id": result.entry_id,
                "comment": result.comment,
                "journal_ref": result.journal_ref,
                "primary_category": result.primary_category
            }
        )

    def get_paper_by_id(self, arxiv_id: str) -> Optional[RawPaper]:
        """특정 arXiv ID로 논문 조회"""
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            result = next(self.client.results(search))
            return self._convert_to_raw_paper(result)
        except StopIteration:
            logger.warning(f"Paper not found: {arxiv_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching paper {arxiv_id}: {e}")
            return None
```

### 4.2 Semantic Scholar Collector

```python
import requests
from typing import List, Optional
from ratelimit import limits, sleep_and_retry
import os

class SemanticScholarCollector:
    """Semantic Scholar API 수집기"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    RATE_LIMIT_CALLS = 100
    RATE_LIMIT_PERIOD = 300  # 5 minutes

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"x-api-key": self.api_key})

    @sleep_and_retry
    @limits(calls=RATE_LIMIT_CALLS, period=RATE_LIMIT_PERIOD)
    def get_paper_details(self, arxiv_id: str) -> Optional[Dict]:
        """arXiv ID로 Semantic Scholar 데이터 조회"""
        url = f"{self.BASE_URL}/paper/arXiv:{arxiv_id}"
        params = {
            "fields": "paperId,externalIds,title,abstract,authors,publicationDate,"
                     "citationCount,referenceCount,influentialCitationCount,"
                     "citations,references,embedding"
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Paper not found in Semantic Scholar: {arxiv_id}")
            else:
                logger.error(f"HTTP error fetching {arxiv_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {arxiv_id}: {e}")
            return None

    def enrich_paper(self, paper: NormalizedPaper) -> NormalizedPaper:
        """Semantic Scholar 데이터로 논문 정보 보강"""
        if not paper.arxiv_id:
            return paper

        s2_data = self.get_paper_details(paper.arxiv_id)
        if not s2_data:
            return paper

        # Add citation information
        paper.raw_metadata.update({
            "semantic_scholar_id": s2_data.get("paperId"),
            "citation_count": s2_data.get("citationCount", 0),
            "reference_count": s2_data.get("referenceCount", 0),
            "influential_citation_count": s2_data.get("influentialCitationCount", 0)
        })

        # Add DOI if available
        external_ids = s2_data.get("externalIds", {})
        if not paper.doi and external_ids.get("DOI"):
            paper.doi = external_ids["DOI"]

        return paper
```

### 4.3 Papers with Code Collector

```python
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

class PapersWithCodeCollector:
    """Papers with Code 수집기"""

    BASE_URL = "https://paperswithcode.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; PaperPulse/1.0)"
        })

    def get_implementations(self, arxiv_id: str) -> Optional[Dict]:
        """arXiv ID로 구현체 정보 조회"""
        # Papers with Code는 공식 API가 제한적이므로 웹 스크래핑 사용
        url = f"{self.BASE_URL}/paper/{arxiv_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            implementations = {
                "has_code": False,
                "repositories": [],
                "frameworks": [],
                "datasets": []
            }

            # Find code repositories
            repo_section = soup.find('div', class_='paper-implementations')
            if repo_section:
                implementations["has_code"] = True
                repo_links = repo_section.find_all('a', href=True)
                implementations["repositories"] = [
                    {
                        "url": link['href'],
                        "name": link.text.strip(),
                        "stars": self._extract_stars(link)
                    }
                    for link in repo_links if 'github.com' in link['href']
                ]

            return implementations
        except Exception as e:
            logger.error(f"Error fetching Papers with Code data: {e}")
            return None

    def _extract_stars(self, link) -> Optional[int]:
        """GitHub stars 추출"""
        stars_span = link.find('span', class_='stars')
        if stars_span:
            try:
                return int(stars_span.text.strip().replace(',', ''))
            except ValueError:
                pass
        return None
```

---

## 5. 정규화 및 중복 제거

### 5.1 Normalizer

```python
class PaperNormalizer:
    """논문 데이터 정규화"""

    def normalize(self, raw_paper: RawPaper) -> NormalizedPaper:
        """RawPaper를 NormalizedPaper로 변환"""

        # Extract IDs based on source
        arxiv_id = None
        doi = None
        semantic_scholar_id = None

        if raw_paper.source == DataSource.ARXIV:
            arxiv_id = raw_paper.external_id
        elif raw_paper.source == DataSource.SEMANTIC_SCHOLAR:
            semantic_scholar_id = raw_paper.external_id
            # Extract arXiv ID from external IDs if available
            if "arXiv" in raw_paper.raw_metadata.get("externalIds", {}):
                arxiv_id = raw_paper.raw_metadata["externalIds"]["arXiv"]
            if "DOI" in raw_paper.raw_metadata.get("externalIds", {}):
                doi = raw_paper.raw_metadata["externalIds"]["DOI"]

        # Normalize title
        title = self._normalize_title(raw_paper.title)

        # Normalize abstract
        abstract = self._normalize_abstract(raw_paper.abstract)

        # Extract primary category
        primary_category = raw_paper.categories[0] if raw_paper.categories else None

        # Create normalized paper
        normalized = NormalizedPaper(
            arxiv_id=arxiv_id,
            doi=doi,
            semantic_scholar_id=semantic_scholar_id,
            title=title,
            abstract=abstract,
            authors=raw_paper.authors,
            published_at=raw_paper.published_at,
            updated_at=raw_paper.updated_at,
            categories=raw_paper.categories,
            primary_category=primary_category,
            pdf_url=raw_paper.pdf_url,
            data_source=raw_paper.source,
            raw_metadata=raw_paper.raw_metadata
        )

        # Compute hashes for deduplication
        normalized.compute_hashes()

        return normalized

    def _normalize_title(self, title: str) -> str:
        """제목 정규화"""
        import re

        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title)

        # Remove leading/trailing whitespace
        title = title.strip()

        # Remove LaTeX commands
        title = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', title)

        return title

    def _normalize_abstract(self, abstract: Optional[str]) -> Optional[str]:
        """초록 정규화"""
        if not abstract:
            return None

        import re

        # Remove extra whitespace
        abstract = re.sub(r'\s+', ' ', abstract)

        # Remove leading/trailing whitespace
        abstract = abstract.strip()

        return abstract
```

### 5.2 Deduplicator

```python
from sqlalchemy.orm import Session

class PaperDeduplicator:
    """논문 중복 감지 및 제거"""

    def __init__(self, db: Session):
        self.db = db

    def find_duplicates(self, paper: NormalizedPaper) -> Optional[str]:
        """중복 논문 검색, 있으면 기존 paper_id 반환"""

        # Strategy 1: arXiv ID로 검색
        if paper.arxiv_id:
            existing = self.db.query(PaperFingerprint).filter(
                PaperFingerprint.arxiv_id == paper.arxiv_id
            ).first()
            if existing:
                logger.info(f"Duplicate found via arXiv ID: {paper.arxiv_id}")
                return existing.paper_id

        # Strategy 2: DOI로 검색
        if paper.doi:
            existing = self.db.query(PaperFingerprint).filter(
                PaperFingerprint.doi == paper.doi
            ).first()
            if existing:
                logger.info(f"Duplicate found via DOI: {paper.doi}")
                return existing.paper_id

        # Strategy 3: Title + Author hash로 검색
        existing = self.db.query(PaperFingerprint).filter(
            PaperFingerprint.title_hash == paper.title_hash,
            PaperFingerprint.author_hash == paper.author_hash
        ).first()
        if existing:
            logger.info(f"Duplicate found via title+author hash: {paper.title[:50]}")
            return existing.paper_id

        # Strategy 4: Fuzzy title matching (레벤슈타인 거리)
        similar = self._fuzzy_title_search(paper.title)
        if similar:
            logger.info(f"Potential duplicate found via fuzzy match: {paper.title[:50]}")
            return similar.paper_id

        return None

    def _fuzzy_title_search(self, title: str, threshold: float = 0.9) -> Optional[PaperFingerprint]:
        """퍼지 매칭으로 유사 제목 검색"""
        from difflib import SequenceMatcher

        # 최근 1000개 논문만 검색 (성능 고려)
        recent_papers = self.db.query(Paper).order_by(
            Paper.published_at.desc()
        ).limit(1000).all()

        for existing_paper in recent_papers:
            similarity = SequenceMatcher(
                None,
                title.lower(),
                existing_paper.title.lower()
            ).ratio()

            if similarity >= threshold:
                fingerprint = self.db.query(PaperFingerprint).filter(
                    PaperFingerprint.paper_id == existing_paper.id
                ).first()
                return fingerprint

        return None

    def merge_metadata(self, existing_id: str, new_paper: NormalizedPaper) -> Paper:
        """중복 논문의 메타데이터 병합"""
        existing = self.db.query(Paper).filter(Paper.id == existing_id).first()

        # Update fields if new data is more complete
        if new_paper.doi and not existing.doi:
            existing.doi = new_paper.doi

        if new_paper.semantic_scholar_id and not existing.semantic_scholar_id:
            existing.semantic_scholar_id = new_paper.semantic_scholar_id

        # Merge categories
        existing.categories = list(set(existing.categories + new_paper.categories))

        # Update metadata
        existing.raw_metadata.update(new_paper.raw_metadata)
        existing.last_updated = datetime.utcnow()

        self.db.commit()
        return existing
```

---

## 6. 에러 핸들링 및 재시도

### 6.1 Error Handler

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class IngestionErrorHandler:
    """수집 에러 처리 및 재시도"""

    def __init__(self, db: Session):
        self.db = db

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def retry_with_backoff(self, func, *args, **kwargs):
        """지수 백오프 재시도"""
        return func(*args, **kwargs)

    def log_failure(self, source: str, external_id: str,
                   raw_data: Dict, error: Exception):
        """실패 로그 저장"""
        failure = IngestionFailure(
            source=source,
            external_id=external_id,
            raw_data=raw_data,
            error_type=type(error).__name__,
            error_message=str(error),
            retry_count=0,
            next_retry_at=datetime.utcnow() + timedelta(minutes=5)
        )

        self.db.add(failure)
        self.db.commit()

        logger.error(f"Logged ingestion failure: {source}/{external_id} - {error}")

    def retry_failures(self):
        """실패한 수집 작업 재시도"""
        failures = self.db.query(IngestionFailure).filter(
            IngestionFailure.status == 'pending',
            IngestionFailure.retry_count < IngestionFailure.max_retries,
            IngestionFailure.next_retry_at <= datetime.utcnow()
        ).all()

        for failure in failures:
            try:
                # 소스별로 적절한 collector 선택
                collector = self._get_collector(failure.source)

                # 재시도
                paper = collector.get_paper_by_id(failure.external_id)
                if paper:
                    # 성공 시 resolved로 마킹
                    failure.status = 'resolved'
                    failure.resolved_at = datetime.utcnow()
                    logger.info(f"Successfully retried: {failure.source}/{failure.external_id}")
                else:
                    self._increment_retry(failure)
            except Exception as e:
                logger.error(f"Retry failed: {failure.source}/{failure.external_id} - {e}")
                self._increment_retry(failure)

        self.db.commit()

    def _increment_retry(self, failure: IngestionFailure):
        """재시도 카운트 증가 및 다음 재시도 시간 설정"""
        failure.retry_count += 1

        if failure.retry_count >= failure.max_retries:
            failure.status = 'failed'
            logger.warning(f"Max retries reached: {failure.source}/{failure.external_id}")
        else:
            # 지수 백오프
            delay_minutes = 2 ** failure.retry_count
            failure.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
```

---

## 7. Celery Tasks

### 7.1 Task 정의

```python
from celery import Celery, Task
from celery.schedules import crontab

app = Celery('paperpulse')

app.conf.beat_schedule = {
    'ingest-arxiv-daily': {
        'task': 'tasks.ingest_arxiv',
        'schedule': crontab(hour=2, minute=0),  # 매일 02:00 UTC
    },
    'enrich-semantic-scholar': {
        'task': 'tasks.enrich_from_semantic_scholar',
        'schedule': crontab(hour='*/4'),  # 4시간마다
    },
    'retry-failures': {
        'task': 'tasks.retry_failed_ingestions',
        'schedule': crontab(minute='*/30'),  # 30분마다
    },
}

@app.task(bind=True, max_retries=3)
def ingest_arxiv(self):
    """arXiv 논문 수집 태스크"""
    try:
        # Get last checkpoint
        checkpoint = get_last_checkpoint(DataSource.ARXIV)
        since = checkpoint.last_sync_time if checkpoint else datetime.utcnow() - timedelta(days=1)

        # Collect papers
        collector = ArxivCollector()
        raw_papers = collector.collect_since(since)

        # Process papers
        normalizer = PaperNormalizer()
        deduplicator = PaperDeduplicator(db)
        stored_count = 0

        for raw_paper in raw_papers:
            normalized = normalizer.normalize(raw_paper)

            # Check duplicates
            duplicate_id = deduplicator.find_duplicates(normalized)
            if duplicate_id:
                deduplicator.merge_metadata(duplicate_id, normalized)
            else:
                store_paper(normalized)
                stored_count += 1

        # Update checkpoint
        update_checkpoint(DataSource.ARXIV, datetime.utcnow(), stored_count)

        logger.info(f"arXiv ingestion completed: {stored_count} new papers")
        return {"status": "success", "papers_stored": stored_count}

    except Exception as exc:
        logger.error(f"arXiv ingestion failed: {exc}")
        raise self.retry(exc=exc, countdown=300)  # 5분 후 재시도

@app.task
def enrich_from_semantic_scholar():
    """Semantic Scholar로 논문 정보 보강"""
    # 최근 24시간 이내 수집된 논문 중 enrichment 안 된 것들 처리
    papers = db.query(Paper).filter(
        Paper.ingested_at >= datetime.utcnow() - timedelta(days=1),
        Paper.semantic_scholar_id == None
    ).limit(100).all()

    collector = SemanticScholarCollector()

    for paper in papers:
        enriched = collector.enrich_paper(paper)
        db.merge(enriched)

    db.commit()
    logger.info(f"Enriched {len(papers)} papers from Semantic Scholar")

@app.task
def retry_failed_ingestions():
    """실패한 수집 작업 재시도"""
    error_handler = IngestionErrorHandler(db)
    error_handler.retry_failures()
```

---

## 8. API 인터페이스

### 8.1 REST API Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/ingestion", tags=["Ingestion"])

@router.post("/trigger/{source}")
async def trigger_ingestion(
    source: str,
    background_tasks: BackgroundTasks,
    since: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """수집 작업 수동 트리거"""

    if source not in ["arxiv", "semantic_scholar", "papers_with_code"]:
        raise HTTPException(status_code=400, detail="Invalid source")

    # Background task로 실행
    if source == "arxiv":
        background_tasks.add_task(ingest_arxiv)
    elif source == "semantic_scholar":
        background_tasks.add_task(enrich_from_semantic_scholar)

    return {"status": "triggered", "source": source}

@router.get("/status")
async def get_ingestion_status(db: Session = Depends(get_db)):
    """수집 상태 조회"""

    checkpoints = db.query(IngestionCheckpoint).order_by(
        IngestionCheckpoint.created_at.desc()
    ).limit(10).all()

    failure_count = db.query(IngestionFailure).filter(
        IngestionFailure.status.in_(['pending', 'retrying'])
    ).count()

    return {
        "recent_checkpoints": [
            {
                "source": cp.source,
                "last_sync": cp.last_sync_time,
                "papers_collected": cp.papers_collected,
                "status": cp.status
            }
            for cp in checkpoints
        ],
        "pending_failures": failure_count
    }

@router.get("/failures")
async def get_failures(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """실패 로그 조회"""

    failures = db.query(IngestionFailure).filter(
        IngestionFailure.status != 'resolved'
    ).order_by(
        IngestionFailure.created_at.desc()
    ).limit(limit).all()

    return {
        "failures": [
            {
                "id": f.id,
                "source": f.source,
                "external_id": f.external_id,
                "error_type": f.error_type,
                "error_message": f.error_message,
                "retry_count": f.retry_count,
                "next_retry_at": f.next_retry_at
            }
            for f in failures
        ]
    }
```

---

## 9. 모니터링 및 메트릭

### 9.1 Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
papers_ingested_total = Counter(
    'papers_ingested_total',
    'Total number of papers ingested',
    ['source']
)

ingestion_errors_total = Counter(
    'ingestion_errors_total',
    'Total number of ingestion errors',
    ['source', 'error_type']
)

duplicates_found_total = Counter(
    'duplicates_found_total',
    'Total number of duplicate papers found',
    ['source']
)

# Histograms
ingestion_duration_seconds = Histogram(
    'ingestion_duration_seconds',
    'Time spent ingesting papers',
    ['source'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

# Gauges
pending_failures = Gauge(
    'pending_ingestion_failures',
    'Number of pending failed ingestions'
)
```

### 9.2 Logging

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """로깅 설정"""

    logger = logging.getLogger('paperpulse.ingestion')
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        'logs/ingestion.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
```

---

## 10. 테스트 전략

### 10.1 Unit Tests

```python
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

class TestArxivCollector:

    def test_collect_since(self):
        """특정 시점 이후 논문 수집 테스트"""
        collector = ArxivCollector()
        since = datetime(2025, 11, 1)

        with patch.object(collector.client, 'results') as mock_results:
            # Mock arXiv results
            mock_results.return_value = [
                Mock(
                    entry_id="2311.12345",
                    title="Test Paper",
                    summary="Test abstract",
                    authors=[Mock(name="John Doe")],
                    published=datetime(2025, 11, 2),
                    categories=["cs.AI"]
                )
            ]

            papers = collector.collect_since(since)

            assert len(papers) == 1
            assert papers[0].title == "Test Paper"
            assert papers[0].source == DataSource.ARXIV

class TestPaperNormalizer:

    def test_normalize_title(self):
        """제목 정규화 테스트"""
        normalizer = PaperNormalizer()

        # LaTeX 제거
        title = "\\textbf{Attention} is All You Need"
        normalized = normalizer._normalize_title(title)
        assert normalized == "Attention is All You Need"

        # 여러 공백 제거
        title = "Multiple   Spaces   Here"
        normalized = normalizer._normalize_title(title)
        assert normalized == "Multiple Spaces Here"

class TestDeduplicator:

    @pytest.fixture
    def db_session(self):
        # In-memory SQLite for testing
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    def test_find_duplicates_by_arxiv_id(self, db_session):
        """arXiv ID로 중복 감지 테스트"""
        deduplicator = PaperDeduplicator(db_session)

        # 기존 논문 저장
        existing = Paper(
            arxiv_id="2311.12345",
            title="Test Paper",
            authors=[],
            published_at=datetime.now()
        )
        db_session.add(existing)
        db_session.commit()

        # 중복 검사
        new_paper = NormalizedPaper(
            arxiv_id="2311.12345",
            title="Test Paper",
            authors=[]
        )

        duplicate_id = deduplicator.find_duplicates(new_paper)
        assert duplicate_id == existing.id
```

### 10.2 Integration Tests

```python
class TestIngestionPipeline:

    @pytest.mark.integration
    def test_end_to_end_arxiv_ingestion(self):
        """arXiv 수집 E2E 테스트"""

        # 1. Collect
        collector = ArxivCollector()
        papers = collector.collect_since(datetime.now() - timedelta(days=1))
        assert len(papers) > 0

        # 2. Normalize
        normalizer = PaperNormalizer()
        normalized = normalizer.normalize(papers[0])
        assert normalized.title_hash is not None

        # 3. Deduplicate
        deduplicator = PaperDeduplicator(db)
        duplicate_id = deduplicator.find_duplicates(normalized)

        # 4. Store
        if not duplicate_id:
            stored = store_paper(normalized)
            assert stored.id is not None
```

---

## 11. 배포 및 운영

### 11.1 Docker Compose

```yaml
version: '3.8'

services:
  ingestion-worker:
    build:
      context: .
      dockerfile: Dockerfile.ingestion
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/paperpulse
      - REDIS_URL=redis://redis:6379/0
      - SEMANTIC_SCHOLAR_API_KEY=${SEMANTIC_SCHOLAR_API_KEY}
    depends_on:
      - postgres
      - redis
    command: celery -A tasks worker --loglevel=info
    volumes:
      - ./logs:/app/logs

  ingestion-beat:
    build:
      context: .
      dockerfile: Dockerfile.ingestion
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/paperpulse
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: celery -A tasks beat --loglevel=info

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=paperpulse
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 11.2 모니터링 대시보드

Grafana 대시보드에서 모니터링할 주요 지표:

- **수집 처리량**: papers_ingested_total (시간당)
- **에러율**: ingestion_errors_total / papers_ingested_total
- **중복률**: duplicates_found_total / papers_ingested_total
- **실패 큐 크기**: pending_ingestion_failures
- **수집 지연**: 현재 시간 - last_sync_time
- **소스별 처리 시간**: ingestion_duration_seconds

---

## 12. 성능 최적화

### 12.1 병렬 처리

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

class ParallelCollector:
    """병렬 수집기"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers

    def collect_from_multiple_sources(self, since: datetime) -> List[RawPaper]:
        """여러 소스에서 동시 수집"""

        collectors = {
            "arxiv": ArxivCollector(),
            "semantic_scholar": SemanticScholarCollector(),
            "papers_with_code": PapersWithCodeCollector()
        }

        all_papers = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(collector.collect_since, since): source
                for source, collector in collectors.items()
            }

            for future in as_completed(futures):
                source = futures[future]
                try:
                    papers = future.result()
                    all_papers.extend(papers)
                    logger.info(f"Collected {len(papers)} from {source}")
                except Exception as e:
                    logger.error(f"Error collecting from {source}: {e}")

        return all_papers
```

### 12.2 배치 처리

```python
def batch_store_papers(papers: List[NormalizedPaper], batch_size: int = 100):
    """배치로 논문 저장"""

    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]

        # Bulk insert
        db.bulk_insert_mappings(Paper, [p.dict() for p in batch])
        db.commit()

        logger.info(f"Stored batch {i//batch_size + 1}: {len(batch)} papers")
```

---

## 13. 보안 고려사항

1. **API Key 관리**: 환경 변수로 관리, Vault 사용 권장
2. **Rate Limiting**: 외부 API 호출 제한 준수
3. **데이터 검증**: 입력 데이터 sanitization
4. **에러 로깅**: 민감 정보 마스킹
5. **접근 제어**: 관리 API에 인증 적용

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14
**다음 리뷰:** 2025-12-14

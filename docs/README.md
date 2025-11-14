# PaperPulse - 설계 문서

AI/LLM 논문 트래킹 시스템 (PaperPulse)의 전체 설계 문서입니다.

## 📚 문서 구조

```
docs/
├── README.md                           # 이 파일
├── design/
│   ├── architecture/
│   │   └── 00-system-architecture.md  # 전체 시스템 아키텍처
│   └── modules/
│       ├── 01-data-ingestion-pipeline.md     # 데이터 수집 모듈
│       ├── 02-pdf-processing.md              # PDF 처리 모듈
│       ├── 03-embedding-vector-store.md      # 임베딩 & 벡터 저장소
│       ├── 04-knowledge-graph.md             # 지식 그래프
│       ├── 05-notification-recommendation.md # 알림 & 추천
│       └── 06-search-and-qa.md               # 검색 & 질의응답
```

## 🎯 프로젝트 개요

**PaperPulse**는 AI 및 LLM 관련 최신 연구 논문을 자동으로 수집, 분석, 분류하고 사용자에게 맞춤형 인사이트를 제공하는 지능형 논문 트래킹 시스템입니다.

### 핵심 가치

- ⚡ **Time-to-Insight 최소화**: 논문 발표 후 24시간 내 인사이트 제공
- 🧠 **Context-Aware Retrieval**: 논문 간 관계와 맥락을 이해하는 검색
- 🎨 **Personalized Discovery**: 사용자 관심사 기반 맞춤 추천
- 🕸️ **Knowledge Graph**: 연구 트렌드와 개념 간 연결 시각화

## 🏗️ 시스템 아키텍처

### 레이어 구조

```
┌─────────────────────────────────────────┐
│      Presentation Layer                 │  ← Web UI, REST API
├─────────────────────────────────────────┤
│      Orchestration Layer                │  ← LangGraph Agents
├─────────────────────────────────────────┤
│      Business Logic Layer               │  ← Core Services
├─────────────────────────────────────────┤
│      Data Access Layer                  │  ← ORM, Cache
├─────────────────────────────────────────┤
│      Storage Layer                      │  ← PostgreSQL, Redis, S3
└─────────────────────────────────────────┘
```

### 핵심 모듈

1. **Data Ingestion Pipeline**
   - arXiv, Semantic Scholar, Papers with Code 연동
   - 중복 제거 및 메타데이터 정규화
   - 에러 복구 및 재시도 메커니즘

2. **PDF Processing**
   - Multi-parser 아키텍처 (PyMuPDF, pdfplumber, Tesseract)
   - 섹션 자동 분할
   - 테이블/이미지 추출

3. **Embedding & Vector Store**
   - BGE-M3 기반 Dense + Sparse 벡터 생성
   - pgvector HNSW 인덱스
   - 다중 레벨 임베딩 (문서, 섹션, 청크)

4. **Knowledge Graph**
   - LightRAG 통합
   - 엔티티/관계 자동 추출
   - 그래프 기반 쿼리 및 추론

5. **Notification & Recommendation**
   - 사용자 프로필 학습
   - 다중 전략 하이브리드 추천
   - Multi-channel 알림 (Email, Slack, Push)

6. **Semantic Search & QA**
   - Vector + Graph 하이브리드 검색
   - 자연어 질의응답
   - 인용 기반 답변 생성

## 🔧 기술 스택

| Category | Technology |
|----------|-----------|
| **Backend** | Python 3.11+, FastAPI |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache** | Redis Cluster |
| **Message Queue** | Celery + Redis |
| **Vector Search** | pgvector (HNSW) |
| **Knowledge Graph** | LightRAG + NetworkX |
| **Embeddings** | BGE-M3, OpenAI text-embedding-3 |
| **LLM** | GPT-4o-mini, Claude Sonnet |
| **Frontend** | React + TypeScript |
| **Deployment** | Docker, Kubernetes |
| **Monitoring** | Prometheus + Grafana |

## 📖 문서 읽기 순서

### 신규 개발자

1. **[시스템 아키텍처](design/architecture/00-system-architecture.md)** - 전체 구조 이해
2. **[Data Ingestion](design/modules/01-data-ingestion-pipeline.md)** - 데이터 수집 플로우
3. **[PDF Processing](design/modules/02-pdf-processing.md)** - 문서 처리 방식
4. **[Embedding & Vector Store](design/modules/03-embedding-vector-store.md)** - 검색 기반

### 검색/추천 개발자

1. **[Embedding & Vector Store](design/modules/03-embedding-vector-store.md)**
2. **[Knowledge Graph](design/modules/04-knowledge-graph.md)**
3. **[Search & QA](design/modules/06-search-and-qa.md)**
4. **[Notification & Recommendation](design/modules/05-notification-recommendation.md)**

### 인프라 엔지니어

1. **[시스템 아키텍처](design/architecture/00-system-architecture.md)**
2. 각 모듈의 "배포 및 운영" 섹션

## 🚀 구현 로드맵

### Phase 1: MVP (8주)
- ✅ arXiv API 연동
- ✅ 기본 PDF 텍스트 추출
- ✅ BGE-M3 임베딩 생성
- ✅ pgvector 저장 및 검색
- ✅ 기본 Web UI
- ✅ 키워드 기반 알림

### Phase 2: Enhanced Search (6주)
- ⬜ Semantic Scholar 연동
- ⬜ Papers with Code 연동
- ⬜ 하이브리드 검색 구현
- ⬜ 고급 필터링 UI
- ⬜ 사용자 북마크/컬렉션

### Phase 3: Knowledge Graph (8주)
- ⬜ LightRAG 통합
- ⬜ 엔티티/관계 추출
- ⬜ 그래프 시각화
- ⬜ 연구 경로 추적
- ⬜ 질의응답 시스템

### Phase 4: Personalization (6주)
- ⬜ 사용자 프로필 모델링
- ⬜ 추천 엔진 구현
- ⬜ 관심사 학습
- ⬜ 개인화 대시보드
- ⬜ 트렌드 예측

## 📊 성능 목표

| Metric | Target | Current |
|--------|--------|---------|
| API Latency (p95) | < 500ms | TBD |
| Search Latency (p95) | < 800ms | TBD |
| PDF Processing | < 30s/paper | TBD |
| Embedding Generation | < 5s/paper | TBD |
| System Availability | 99.5% | TBD |

## 🤝 기여 가이드

### 문서 업데이트

1. 모듈 설계 변경 시 해당 문서 업데이트
2. 버전 번호 증가
3. "최종 업데이트" 날짜 갱신
4. Pull Request 생성

### 문서 작성 규칙

- **제목**: 명확하고 간결하게
- **코드 예제**: 실제 동작하는 코드 우선
- **다이어그램**: ASCII 또는 Mermaid 사용
- **데이터베이스 스키마**: SQL DDL 제공
- **API**: Request/Response 예제 포함

## 📞 문의

- **프로젝트 리드**: [Your Name]
- **기술 문의**: tech@paperpulse.ai
- **이슈 트래킹**: GitHub Issues

## 📄 라이선스

[MIT License](../LICENSE)

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-11-14
**다음 리뷰**: 2025-12-14

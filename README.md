# PaperPulse 🔬

> AI/LLM 논문을 위한 지능형 트래킹 및 인사이트 시스템

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-comprehensive-green.svg)](docs/README.md)

## 📋 목차

- [프로젝트 개요](#-프로젝트-개요)
- [핵심 기능](#-핵심-기능)
- [아키텍처](#-아키텍처)
- [기술 스택](#-기술-스택)
- [시작하기](#-시작하기)
- [문서](#-문서)
- [개발 현황](#-개발-현황)
- [기여하기](#-기여하기)
- [라이선스](#-라이선스)

## 🎯 프로젝트 개요

**PaperPulse**는 AI 및 LLM 분야의 최신 연구 논문을 자동으로 수집, 분석, 분류하고 개인화된 인사이트를 제공하는 지능형 논문 트래킹 시스템입니다.

### 핵심 가치 제안

- ⚡ **빠른 인사이트**: 논문 발표 후 24시간 내 핵심 내용 파악
- 🧠 **컨텍스트 인식 검색**: 논문 간 관계와 맥락을 이해하는 시맨틱 검색
- 🎯 **개인화 추천**: 사용자 관심사 기반 맞춤형 논문 발견
- 🕸️ **지식 그래프**: 연구 트렌드와 개념 간 연결 시각화
- 🔔 **실시간 알림**: 관심 분야 새 논문 즉시 알림

### 주요 사용 사례

1. **연구자**: 최신 연구 동향 파악 및 관련 논문 발견
2. **학생**: 특정 주제에 대한 포괄적인 문헌 조사
3. **개발자**: 최신 기술 트렌드 및 구현 방법 학습
4. **기업**: 경쟁 기술 분석 및 연구 방향 설정

## ✨ 핵심 기능

### 📥 자동 논문 수집
- **다중 소스 지원**: arXiv, Semantic Scholar, Papers with Code
- **증분 동기화**: 신규 논문만 효율적으로 수집
- **지능형 중복 제거**: 여러 소스의 동일 논문 통합
- **메타데이터 보강**: 인용 수, 코드 구현 등 추가 정보

### 🔍 고급 검색 및 질의응답
- **하이브리드 검색**: Dense + Sparse 벡터 검색 결합
- **그래프 기반 검색**: 개념 간 관계를 활용한 탐색
- **자연어 QA**: "Transformer는 어떻게 작동하나요?" 같은 질문에 답변
- **비교 분석**: 여러 논문/기법 자동 비교
- **트렌드 분석**: 시간에 따른 연구 발전 추적

### 🎨 개인화 경험
- **관심사 학습**: 사용자 행동 기반 프로필 자동 구축
- **다중 전략 추천**: 콘텐츠 기반 + 협업 필터링 + 지식 그래프
- **맞춤형 알림**: Email, Slack, Push 등 선호 채널로 알림
- **개인 대시보드**: 관심 분야 최신 동향 한눈에 파악

### 🕸️ 지식 그래프
- **자동 엔티티 추출**: 기술, 개념, 저자, 데이터셋 식별
- **관계 매핑**: 논문 간, 개념 간 연결 관계 시각화
- **연구 경로 추적**: 특정 기술의 발전 과정 탐색
- **커뮤니티 발견**: 연구 그룹 및 클러스터 자동 식별

## 🏗️ 아키텍처

### 시스템 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Web UI  │  │ REST API │  │ WebSocket│  │  Webhook │   │
│  │ (React)  │  │ (FastAPI)│  │          │  │  (Slack) │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 ORCHESTRATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Ingestion   │  │    Query     │  │ Notification │     │
│  │    Agent     │  │    Agent     │  │    Agent     │     │
│  │ (LangGraph)  │  │ (LangGraph)  │  │ (LangGraph)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   BUSINESS LOGIC LAYER                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Data        │  │ PDF         │  │ Embedding   │        │
│  │ Ingestion   │  │ Processing  │  │ Generation  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Knowledge   │  │ Search &    │  │ Recommend   │        │
│  │ Graph       │  │ QA          │  │ & Notify    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │    Redis     │  │   S3/Minio   │     │
│  │ + pgvector   │  │    Cache     │  │  (PDF/Images)│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 모듈

| 모듈 | 설명 | 주요 기술 |
|------|------|----------|
| **Data Ingestion** | 다중 소스 논문 수집 및 정규화 | arXiv API, Semantic Scholar, Celery |
| **PDF Processing** | PDF 파싱 및 구조화 | PyMuPDF, pdfplumber, Tesseract OCR |
| **Embedding & Vector Store** | 텍스트 임베딩 및 벡터 검색 | BGE-M3, pgvector, HNSW |
| **Knowledge Graph** | 지식 그래프 구축 및 추론 | LightRAG, NetworkX, SpaCy |
| **Notification & Recommendation** | 개인화 추천 및 알림 | 하이브리드 추천, Email/Slack |
| **Search & QA** | 시맨틱 검색 및 질의응답 | Vector + Graph 검색, GPT-4 |

## 🛠️ 기술 스택

### Backend
- **언어**: Python 3.11+
- **웹 프레임워크**: FastAPI
- **작업 큐**: Celery + Redis
- **워크플로우**: LangGraph

### Database & Storage
- **관계형 DB**: PostgreSQL 16 + pgvector
- **캐시**: Redis Cluster
- **객체 스토리지**: S3 / MinIO
- **벡터 검색**: pgvector (HNSW 인덱스)

### AI/ML
- **LLM**: GPT-4o-mini, Claude Sonnet
- **임베딩**: BGE-M3 (local), OpenAI text-embedding-3
- **지식 그래프**: LightRAG + NetworkX
- **NER**: SpaCy (SciBERT 기반)
- **PDF OCR**: Tesseract

### Infrastructure
- **컨테이너**: Docker + Kubernetes
- **모니터링**: Prometheus + Grafana
- **로깅**: ELK Stack
- **CI/CD**: GitHub Actions + ArgoCD

### Frontend
- **프레임워크**: React + TypeScript
- **상태 관리**: Redux Toolkit
- **UI 라이브러리**: Material-UI

## 🚀 시작하기

> ⚠️ **주의**: 현재 프로젝트는 설계 단계이며, 구현 코드는 아직 없습니다.

### 사전 요구사항

- Python 3.11 이상
- PostgreSQL 16 + pgvector extension
- Redis 7.x
- Docker (선택사항)

### 설치 (예정)

```bash
# 저장소 클론
git clone https://github.com/your-org/AI-Paper-Tracker.git
cd AI-Paper-Tracker

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (API 키 등)

# 데이터베이스 초기화
alembic upgrade head

# 개발 서버 실행
uvicorn app.main:app --reload
```

### Docker Compose 실행 (예정)

```bash
# 전체 스택 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

## 📚 문서

### 설계 문서

프로젝트의 모든 설계 문서는 [`docs/`](docs/) 디렉토리에 있습니다.

#### 필수 문서

1. **[전체 설계 개요](docs/README.md)** - 프로젝트 전체 구조 이해
2. **[시스템 아키텍처](docs/design/architecture/00-system-architecture.md)** - 레이어 구조 및 기술 스택

#### 모듈별 상세 설계

| 순서 | 모듈 | 문서 | 라인 수 |
|------|------|------|---------|
| 1 | Data Ingestion Pipeline | [01-data-ingestion-pipeline.md](docs/design/modules/01-data-ingestion-pipeline.md) | 1,348 |
| 2 | PDF Processing | [02-pdf-processing.md](docs/design/modules/02-pdf-processing.md) | 1,149 |
| 3 | Embedding & Vector Store | [03-embedding-vector-store.md](docs/design/modules/03-embedding-vector-store.md) | 1,149 |
| 4 | Knowledge Graph | [04-knowledge-graph.md](docs/design/modules/04-knowledge-graph.md) | 869 |
| 5 | Notification & Recommendation | [05-notification-recommendation.md](docs/design/modules/05-notification-recommendation.md) | 572 |
| 6 | Search & QA | [06-search-and-qa.md](docs/design/modules/06-search-and-qa.md) | 527 |

### 문서 읽기 순서

#### 신규 개발자
1. [프로젝트 개요](docs/README.md)
2. [시스템 아키텍처](docs/design/architecture/00-system-architecture.md)
3. [Data Ingestion](docs/design/modules/01-data-ingestion-pipeline.md)
4. 관심 모듈별 상세 문서

#### 검색/추천 개발자
1. [Embedding & Vector Store](docs/design/modules/03-embedding-vector-store.md)
2. [Knowledge Graph](docs/design/modules/04-knowledge-graph.md)
3. [Search & QA](docs/design/modules/06-search-and-qa.md)
4. [Notification & Recommendation](docs/design/modules/05-notification-recommendation.md)

## 📊 개발 현황

### 🗓️ 로드맵

#### Phase 1: MVP (8주) - 계획 중
- [ ] arXiv API 연동 및 데이터 수집
- [ ] 기본 PDF 텍스트 추출
- [ ] BGE-M3 임베딩 생성 및 저장
- [ ] pgvector 기반 벡터 검색
- [ ] 기본 Web UI 구현
- [ ] 키워드 기반 알림 시스템

#### Phase 2: Enhanced Search (6주)
- [ ] Semantic Scholar 연동
- [ ] Papers with Code 연동
- [ ] 하이브리드 검색 구현
- [ ] 고급 필터링 UI
- [ ] 사용자 북마크 및 컬렉션

#### Phase 3: Knowledge Graph (8주)
- [ ] LightRAG 통합
- [ ] 엔티티 및 관계 자동 추출
- [ ] 그래프 시각화
- [ ] 연구 경로 추적 기능
- [ ] 질의응답 시스템

#### Phase 4: Personalization (6주)
- [ ] 사용자 프로필 모델링
- [ ] 추천 엔진 구현
- [ ] 관심사 자동 학습
- [ ] 개인화 대시보드
- [ ] 트렌드 예측

### 📈 성능 목표

| 메트릭 | 목표 | 현재 상태 |
|--------|------|-----------|
| API 응답 시간 (p95) | < 500ms | 미구현 |
| 검색 응답 시간 (p95) | < 800ms | 미구현 |
| PDF 처리 시간 | < 30초/논문 | 미구현 |
| 임베딩 생성 시간 | < 5초/논문 | 미구현 |
| 시스템 가용성 | 99.5% | 미구현 |
| 일일 논문 처리량 | 1,000+ | 미구현 |

### 🔍 코드 품질

현재 설계 문서 현황:
- ✅ **시스템 아키텍처**: 완료 (485 라인)
- ✅ **모듈 설계 문서**: 6개 모듈 완료 (총 5,614 라인)
- ✅ **데이터베이스 스키마**: 모든 모듈 정의 완료
- ✅ **API 인터페이스**: 모든 모듈 정의 완료
- ⬜ **구현 코드**: 아직 시작 안 함

## 🤝 기여하기

### 기여 방법

1. **Fork** 저장소
2. **Feature 브랜치** 생성 (`git checkout -b feature/AmazingFeature`)
3. **변경사항 커밋** (`git commit -m 'Add some AmazingFeature'`)
4. **브랜치에 Push** (`git push origin feature/AmazingFeature`)
5. **Pull Request** 생성

### 코딩 규칙

- **Python**: PEP 8 준수, type hints 사용
- **문서화**: 모든 public 함수/클래스에 docstring 작성
- **테스트**: 새 기능에 대한 단위 테스트 필수
- **커밋 메시지**: Conventional Commits 형식 사용

### 문서 작성 규칙

- **제목**: 명확하고 간결하게
- **코드 예제**: 실제 동작하는 코드 우선
- **다이어그램**: ASCII 또는 Mermaid 사용
- **스키마**: SQL DDL 제공
- **API**: Request/Response 예제 포함

## 📞 문의 및 지원

- **이슈 트래킹**: [GitHub Issues](https://github.com/your-org/AI-Paper-Tracker/issues)
- **토론**: [GitHub Discussions](https://github.com/your-org/AI-Paper-Tracker/discussions)
- **이메일**: tech@paperpulse.ai

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들을 활용합니다:

- [LangGraph](https://github.com/langchain-ai/langgraph) - 워크플로우 오케스트레이션
- [LightRAG](https://github.com/HKUDS/LightRAG) - 그래프 기반 RAG
- [BGE-M3](https://github.com/FlagOpen/FlagEmbedding) - 다국어 임베딩 모델
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL 벡터 확장
- [FastAPI](https://fastapi.tiangolo.com/) - 현대적인 웹 프레임워크

---

**프로젝트 상태**: 🟡 설계 단계 (구현 시작 전)
**문서 버전**: 1.0.0
**최종 업데이트**: 2025-11-15
**다음 마일스톤**: Phase 1 MVP 구현 시작

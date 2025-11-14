# PaperPulse System Architecture - 전체 설계 개요

**프로젝트:** AI/LLM 논문 트래킹 시스템 (PaperPulse)
**버전:** 1.0
**작성일:** 2025-11-14
**문서 유형:** Architecture Overview

---

## 1. 시스템 개요

### 1.1 아키텍처 원칙

**핵심 원칙:**
- **Modularity**: 각 기능을 독립적인 모듈로 분리
- **Scalability**: 수평 확장 가능한 설계
- **Reliability**: Fault tolerance 및 graceful degradation
- **Observability**: 모든 레이어에서 모니터링 및 로깅
- **Performance**: < 500ms API 응답 시간 목표

### 1.2 기술 스택 요약

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API Gateway | FastAPI | REST API, WebSocket |
| Orchestration | LangGraph | Multi-agent workflows |
| Backend | Python 3.11+ | Core services |
| Database | PostgreSQL 16 + pgvector | Relational + Vector data |
| Cache | Redis | Session, embeddings cache |
| Message Queue | Celery + Redis | Async task processing |
| Knowledge Graph | LightRAG + NetworkX | Graph-based RAG |
| Embeddings | BGE-M3 / OpenAI | Vector generation |
| LLM | GPT-4o-mini / Claude | NLP tasks |
| Frontend | React + TypeScript | Web UI |
| Deployment | Docker + Kubernetes | Container orchestration |

---

## 2. 레이어 아키텍처

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
│                    API GATEWAY LAYER                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              FastAPI Application                     │   │
│  │  - Authentication & Authorization                    │   │
│  │  - Rate Limiting                                     │   │
│  │  - Request Validation                                │   │
│  │  - Response Formatting                               │   │
│  └─────────────────────────────────────────────────────┘   │
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
│                     DATA ACCESS LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ SQLAlchemy   │  │   Redis      │  │   S3/Minio   │     │
│  │   (ORM)      │  │   Client     │  │   Client     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │    Redis     │  │   S3/Minio   │     │
│  │ + pgvector   │  │    Cache     │  │  (PDF/Images)│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL SERVICES LAYER                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  arXiv   │  │ Semantic │  │  OpenAI  │  │  Slack   │   │
│  │   API    │  │ Scholar  │  │   API    │  │  Webhook │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 모듈 간 상호작용

### 3.1 논문 수집 플로우

```
arXiv API
   │
   ▼
Data Ingestion Module
   │
   ├─→ Deduplication Check (PostgreSQL)
   │
   ▼
PDF Processing Module
   │
   ├─→ Store PDF (S3/Minio)
   ├─→ Extract Text/Tables
   │
   ▼
Embedding Generation Module
   │
   ├─→ Generate Vectors (BGE-M3)
   ├─→ Store Embeddings (pgvector)
   │
   ▼
Knowledge Graph Module
   │
   ├─→ Extract Entities/Relations (LLM)
   ├─→ Update Graph (LightRAG)
   │
   ▼
Notification Module
   │
   ├─→ Match User Profiles
   ├─→ Calculate Relevance
   └─→ Send Notifications (Email/Slack)
```

### 3.2 검색 플로우

```
User Query
   │
   ▼
Search Module
   │
   ├─→ Query Analysis (LLM)
   │
   ├─→ Vector Search (pgvector)
   │     └─→ Retrieve similar papers
   │
   ├─→ Graph Search (LightRAG)
   │     └─→ Related concepts/papers
   │
   ├─→ Hybrid Fusion (RRF)
   │
   └─→ Response Generation
       └─→ Return results to user
```

---

## 4. 데이터 흐름

### 4.1 주요 데이터 엔티티

```sql
-- Core Entities
papers
  ├─→ processed_documents
  ├─→ paper_embeddings
  ├─→ chunk_embeddings
  ├─→ kg_entities (via kg_entity_papers)
  └─→ references (extracted_references)

users
  ├─→ user_profiles
  ├─→ user_interactions
  └─→ recommendations

kg_entities
  ├─→ kg_relationships
  └─→ kg_entity_papers
```

### 4.2 데이터베이스 설계 원칙

**정규화:**
- 논문 메타데이터: 3NF
- 사용자 데이터: 3NF
- 그래프 데이터: Property Graph 모델

**비정규화:**
- 임베딩 데이터: 검색 성능 최적화
- 통계 데이터: 집계 쿼리 최적화

**파티셔닝:**
- papers 테이블: 연도별 파티셔닝
- chunk_embeddings: paper_id 기반 해시 파티셔닝

---

## 5. 비동기 작업 처리

### 5.1 Celery Task 구조

```python
# Task Queue Architecture
celery_app
  ├─→ ingestion_queue
  │     ├─→ ingest_arxiv (매일 02:00)
  │     ├─→ enrich_semantic_scholar (4시간마다)
  │     └─→ retry_failures (30분마다)
  │
  ├─→ processing_queue
  │     ├─→ process_pdf
  │     ├─→ generate_embeddings
  │     └─→ extract_entities
  │
  ├─→ notification_queue
  │     ├─→ send_email
  │     ├─→ send_slack
  │     └─→ generate_daily_digest
  │
  └─→ analytics_queue
        ├─→ compute_trends
        └─→ update_recommendations
```

### 5.2 Task Priority

| Priority | Queue | Examples |
|----------|-------|----------|
| High (9) | critical | User-triggered searches, QA |
| Medium (5) | default | PDF processing, embeddings |
| Low (1) | batch | Daily ingestion, analytics |

---

## 6. 캐싱 전략

### 6.1 Redis Cache 구조

```
Redis Keys Structure:

# Embeddings Cache
embedding:{paper_id}:{model}  → Vector data (TTL: 7 days)

# Search Cache
search:{query_hash}:{mode}  → Search results (TTL: 1 hour)

# User Sessions
session:{user_id}  → Session data (TTL: 24 hours)

# Rate Limiting
ratelimit:{user_id}:{endpoint}  → Request count (TTL: 1 minute)

# PDF Cache
pdf:{arxiv_id}  → Processed PDF data (TTL: 30 days)
```

### 6.2 Cache Invalidation

**이벤트 기반:**
- 논문 업데이트 → 해당 paper_id 캐시 삭제
- 사용자 프로필 변경 → 추천 캐시 삭제
- 새 논문 수집 → 검색 캐시 부분 무효화

---

## 7. 보안 아키텍처

### 7.1 인증/인가

```
User Request
   │
   ▼
API Gateway
   │
   ├─→ JWT Validation
   │     └─→ Verify signature, expiry
   │
   ├─→ RBAC Check
   │     └─→ Check user role & permissions
   │
   └─→ Rate Limiting
         └─→ Check request quota
```

### 7.2 보안 계층

**Transport Layer:**
- TLS 1.3 for all communications
- Certificate pinning for mobile apps

**Application Layer:**
- OAuth 2.0 + JWT
- API Key for external integrations
- CORS configuration

**Data Layer:**
- Encryption at rest (AES-256)
- Column-level encryption for sensitive data
- Audit logging for all data access

---

## 8. 모니터링 및 옵저버빌리티

### 8.1 메트릭 수집

```
Prometheus
   ├─→ API Metrics (latency, errors, throughput)
   ├─→ Database Metrics (connections, query time)
   ├─→ Celery Metrics (task count, duration, failures)
   └─→ Custom Metrics (papers ingested, searches performed)

Grafana
   ├─→ System Dashboard
   ├─→ Application Dashboard
   └─→ Business Metrics Dashboard
```

### 8.2 로깅 스택

```
Application Logs
   ├─→ Structured Logging (JSON)
   │
   ▼
Filebeat
   ▼
Elasticsearch
   ▼
Kibana
   └─→ Log Analysis & Visualization
```

### 8.3 분산 트레이싱

```
OpenTelemetry
   ├─→ Trace Context Propagation
   ├─→ Span Collection
   │
   ▼
Jaeger
   └─→ Trace Visualization
```

---

## 9. 확장성 전략

### 9.1 수평 확장

**Stateless Services:**
- API서버: Load balancer 뒤에 N개 인스턴스
- Worker: Celery worker 동적 스케일링
- Frontend: CDN + 다중 리전 배포

**Stateful Services:**
- PostgreSQL: Read replicas (Master-Slave)
- Redis: Redis Cluster (Sharding)

### 9.2 성능 목표

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Latency (p95) | < 500ms | Prometheus |
| Search Latency (p95) | < 800ms | Prometheus |
| PDF Processing | < 30s/paper | Celery metrics |
| Embedding Generation | < 5s/paper | Celery metrics |
| System Availability | 99.5% | Uptime monitoring |

---

## 10. 배포 아키텍처

### 10.1 Kubernetes Deployment

```yaml
Namespaces:
  - paperpulse-prod
      ├─→ Deployments
      │     ├─→ api-server (3 replicas)
      │     ├─→ celery-worker (5 replicas)
      │     ├─→ celery-beat (1 replica)
      │     └─→ frontend (2 replicas)
      │
      ├─→ StatefulSets
      │     ├─→ postgres (1 primary, 2 replicas)
      │     └─→ redis (3 nodes cluster)
      │
      ├─→ Services
      │     ├─→ api-service (LoadBalancer)
      │     ├─→ postgres-service (ClusterIP)
      │     └─→ redis-service (ClusterIP)
      │
      └─→ Ingress
            └─→ HTTPS with cert-manager
```

### 10.2 CI/CD Pipeline

```
Git Push (main branch)
   │
   ▼
GitHub Actions
   │
   ├─→ Run Tests (pytest)
   ├─→ Build Docker Image
   ├─→ Push to Registry
   │
   ▼
ArgoCD (GitOps)
   │
   ├─→ Detect Config Change
   ├─→ Apply to K8s Cluster
   │
   ▼
Rolling Update
   └─→ Zero-downtime deployment
```

---

## 11. 재해 복구

### 11.1 백업 전략

**데이터베이스:**
- Daily full backup
- Hourly incremental backup
- 30 days retention
- Automated restore testing (weekly)

**Object Storage:**
- S3 versioning enabled
- Cross-region replication
- Lifecycle policy (archive after 90 days)

### 11.2 RTO/RPO 목표

| Service | RTO | RPO |
|---------|-----|-----|
| API | 15 min | 1 hour |
| Database | 30 min | 1 hour |
| Search | 1 hour | 4 hours |
| Ingestion | 4 hours | 24 hours |

---

## 12. 비용 최적화

### 12.1 예상 월간 비용 (중규모)

| Component | Cost | Optimization |
|-----------|------|--------------|
| Compute (K8s) | $400 | Auto-scaling, spot instances |
| Database | $200 | Right-sizing, read replicas only when needed |
| Storage | $100 | S3 lifecycle, compression |
| LLM API | $300 | Cache responses, use smaller models |
| Monitoring | $50 | Sample rates, retention policies |
| **Total** | **~$1,050** | |

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14
**다음 리뷰:** 2025-12-14

# PaperPulse 🚀

AI/LLM 연구 논문을 자동으로 수집, 분석, 분류하고 사용자에게 맞춤형 인사이트를 제공하는 지능형 논문 트래킹 시스템

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 주요 기능

- 🔍 **자동 논문 수집**: arXiv, Semantic Scholar, Papers with Code 연동
- 📄 **지능형 PDF 처리**: 텍스트, 테이블, 이미지 자동 추출
- 🧠 **시맨틱 검색**: BGE-M3 임베딩 기반 하이브리드 검색
- 🕸️ **지식 그래프**: LightRAG를 활용한 논문 간 관계 분석
- 💬 **대화형 챗봇**: 자연어로 논문 검색 및 질의응답
- 🎯 **개인화 추천**: 사용자 관심사 기반 맞춤 추천
- 📊 **트렌드 분석**: 연구 동향 및 핫토픽 추적

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────┐
│      Presentation Layer                 │  ← Web UI, REST API, WebSocket
├─────────────────────────────────────────┤
│      Orchestration Layer                │  ← LangGraph Multi-Agents
├─────────────────────────────────────────┤
│      Business Logic Layer               │  ← Core Services
├─────────────────────────────────────────┤
│      Data Access Layer                  │  ← SQLAlchemy, Redis
├─────────────────────────────────────────┤
│      Storage Layer                      │  ← PostgreSQL+pgvector, S3
└─────────────────────────────────────────┘
```

## 🛠️ 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache** | Redis |
| **Task Queue** | Celery |
| **AI/ML** | OpenAI, Anthropic, LangChain, LangGraph |
| **Embeddings** | BGE-M3, OpenAI Embeddings |
| **Knowledge Graph** | LightRAG, NetworkX |
| **Deployment** | Docker, Docker Compose |
| **Monitoring** | Prometheus, Grafana |

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.11 이상
- Docker & Docker Compose
- OpenAI API Key (필수)
- Anthropic API Key (선택)

### 1. 저장소 클론

```bash
git clone https://github.com/cmai-master/AI-Paper-Tracker.git
cd AI-Paper-Tracker
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어서 API 키 등을 설정하세요
```

**필수 설정:**
```env
OPENAI_API_KEY=sk-your-openai-api-key
DATABASE_URL=postgresql://paperpulse:password@localhost:5432/paperpulse
REDIS_URL=redis://localhost:6379/0
```

### 3. Docker로 전체 스택 실행

```bash
# 전체 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f api
```

서비스가 시작되면:
- API 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs
- Flower (Celery 모니터링): http://localhost:5555
- Grafana: http://localhost:3001 (admin/admin)
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### 4. 로컬 개발 환경 (Docker 없이)

```bash
# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
pip install -e .

# 데이터베이스 마이그레이션
alembic upgrade head

# 개발 서버 실행
uvicorn paperpulse.api.main:app --reload
```

## 📖 사용 예시

### 논문 검색

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/search",
    json={
        "query": "Retrieval Augmented Generation",
        "mode": "hybrid",
        "top_k": 10
    }
)

papers = response.json()
```

### 챗봇 대화

```python
import asyncio
import websockets
import json

async def chat():
    uri = "ws://localhost:8000/ws/chat/session-123?user_id=user-1"
    async with websockets.connect(uri) as websocket:
        # 메시지 전송
        await websocket.send(json.dumps({
            "type": "message",
            "content": "최근 RAG 논문 찾아줘"
        }))

        # 응답 수신
        response = await websocket.recv()
        print(json.loads(response))

asyncio.run(chat())
```

### 질의응답

```python
response = httpx.post(
    "http://localhost:8000/api/qa",
    json={
        "question": "Transformer의 attention mechanism이 뭐야?"
    }
)

answer = response.json()
print(f"Answer: {answer['answer']}")
print(f"Citations: {answer['citations']}")
```

## 📊 API 엔드포인트

### 검색 & QA
- `POST /api/search` - 논문 검색
- `POST /api/qa` - 질의응답
- `POST /api/compare` - 논문/기법 비교
- `GET /api/trends/{concept}` - 트렌드 분석

### 논문 관리
- `GET /api/papers` - 논문 목록
- `GET /api/papers/{paper_id}` - 논문 상세
- `POST /api/papers/{paper_id}/bookmark` - 북마크 추가

### 추천
- `GET /api/recommendations` - 개인화 추천
- `GET /api/recommendations/trending` - 트렌딩 논문

### 챗봇
- `WS /ws/chat/{session_id}` - 챗봇 WebSocket
- `POST /api/chat/sessions` - 세션 생성
- `GET /api/chat/sessions/{session_id}/messages` - 대화 히스토리

자세한 API 문서는 http://localhost:8000/docs 에서 확인하세요.

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=paperpulse --cov-report=html

# 특정 모듈만 테스트
pytest tests/services/test_search.py
```

## 📁 프로젝트 구조

```
AI-Paper-Tracker/
├── docs/                           # 설계 문서
│   ├── design/
│   │   ├── architecture/           # 시스템 아키텍처
│   │   └── modules/                # 모듈별 설계
├── src/paperpulse/                 # 소스 코드
│   ├── api/                        # FastAPI 라우터
│   ├── models/                     # SQLAlchemy 모델
│   ├── services/                   # 비즈니스 로직
│   │   ├── ingestion/              # 데이터 수집
│   │   ├── pdf/                    # PDF 처리
│   │   ├── embedding/              # 임베딩 생성
│   │   ├── knowledge_graph/        # 지식 그래프
│   │   ├── recommendation/         # 추천
│   │   ├── search/                 # 검색 & QA
│   │   └── chatbot/                # 챗봇
│   ├── agents/                     # LangGraph agents
│   ├── db/                         # 데이터베이스 설정
│   ├── config/                     # 설정
│   └── utils/                      # 유틸리티
├── tests/                          # 테스트
├── docker/                         # Docker 설정
├── scripts/                        # 유틸리티 스크립트
├── requirements.txt                # Python 의존성
├── pyproject.toml                  # 프로젝트 설정
└── docker-compose.yml              # Docker Compose 설정
```

## 🔧 개발 가이드

### 코드 스타일

```bash
# 포맷팅
black src/ tests/

# 린팅
flake8 src/ tests/

# 타입 체크
mypy src/
```

### 데이터베이스 마이그레이션

```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "Add new table"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

### Celery 작업 추가

```python
from paperpulse.workers.celery_app import celery_app

@celery_app.task(queue='processing_queue')
def process_new_paper(paper_id: str):
    # 작업 로직
    pass
```

## 📈 모니터링

### Prometheus 메트릭
- API 요청 수/지연시간
- 데이터베이스 쿼리 성능
- Celery 작업 통계
- 캐시 히트율

### Grafana 대시보드
- 시스템 개요
- API 성능
- 비즈니스 메트릭

http://localhost:3001 에서 확인 (admin/admin)

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 문의

- GitHub Issues: [Create an issue](https://github.com/cmai-master/AI-Paper-Tracker/issues)
- Email: team@paperpulse.ai

## 🙏 감사의 말

- [LangChain](https://langchain.com) - Agent orchestration
- [LightRAG](https://github.com/HKUDS/LightRAG) - Knowledge graph RAG
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [FastAPI](https://fastapi.tiangolo.com) - Modern web framework

---

**Built with ❤️ for the AI research community**

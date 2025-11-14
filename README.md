# PaperPulse - AI/LLM Paper Tracking System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.2+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109+-009688.svg)](https://fastapi.tiangolo.com/)

PaperPulse는 AI 및 LLM 관련 최신 연구 논문을 자동으로 수집, 분석, 분류하고 사용자에게 맞춤형 인사이트를 제공하는 지능형 논문 트래킹 시스템입니다.

## 🎯 핵심 기능

- ⚡ **자동 논문 수집**: arXiv, Semantic Scholar 등에서 최신 논문 자동 수집
- 📄 **PDF 처리**: 고급 PDF 파싱 및 텍스트 추출
- 🔍 **시맨틱 검색**: BGE-M3 임베딩 기반 벡터 검색
- 🕸️ **지식 그래프**: LightRAG를 활용한 논문 간 관계 분석
- 🎨 **개인화 추천**: 사용자 관심사 기반 맞춤 추천
- 🔔 **알림 시스템**: 이메일, Slack을 통한 실시간 알림

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────┐
│      Frontend (React + TypeScript)      │
├─────────────────────────────────────────┤
│      API Gateway (FastAPI)              │
├─────────────────────────────────────────┤
│      Business Logic Layer               │
│  - Data Ingestion                       │
│  - PDF Processing                       │
│  - Embeddings & Search                  │
│  - Knowledge Graph                      │
│  - Recommendations                      │
├─────────────────────────────────────────┤
│      Storage Layer                      │
│  - PostgreSQL + pgvector                │
│  - Redis Cache                          │
│  - S3/MinIO (PDF storage)               │
└─────────────────────────────────────────┘
```

## 🚀 빠른 시작

### 필수 요구사항

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16 (pgvector 확장 지원)
- Redis 7+

### 설치 및 실행

1. **저장소 클론**
```bash
git clone https://github.com/yourusername/paperpulse.git
cd paperpulse
```

2. **환경 변수 설정**
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 API 키 설정
```

3. **Docker Compose로 실행**
```bash
docker-compose up -d
```

4. **데이터베이스 마이그레이션**
```bash
docker-compose exec backend alembic upgrade head
```

5. **접속**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API 문서: http://localhost:8000/api/docs
- Flower (Celery 모니터링): http://localhost:5555

### 로컬 개발 환경

#### Backend

```bash
cd backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements-dev.txt

# 환경 변수 설정
cp ../.env.example ../.env
# .env 파일 편집

# 데이터베이스 마이그레이션
alembic upgrade head

# 개발 서버 실행
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend

# 의존성 설치
npm install

# 환경 변수 설정
cp .env.example .env

# 개발 서버 실행
npm run dev
```

## 📚 문서

자세한 문서는 `docs/` 디렉토리를 참조하세요:

- [시스템 아키텍처](docs/design/architecture/00-system-architecture.md)
- [데이터 수집 모듈](docs/design/modules/01-data-ingestion-pipeline.md)
- [PDF 처리 모듈](docs/design/modules/02-pdf-processing.md)
- [임베딩 & 벡터 저장소](docs/design/modules/03-embedding-vector-store.md)
- [지식 그래프](docs/design/modules/04-knowledge-graph.md)
- [검색 & QA](docs/design/modules/06-search-and-qa.md)

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL 16 + pgvector
- **Cache**: Redis
- **Task Queue**: Celery
- **ORM**: SQLAlchemy 2.0 (async)
- **Embeddings**: BGE-M3, OpenAI text-embedding-3
- **LLM**: GPT-4o-mini, Claude Sonnet
- **Knowledge Graph**: LightRAG + NetworkX

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Router**: React Router v6

### DevOps
- **Containerization**: Docker
- **Orchestration**: Kubernetes (production)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana

## 📦 프로젝트 구조

```
AI-Paper-Tracker/
├── backend/
│   ├── app/
│   │   ├── api/              # API 라우터 및 스키마
│   │   ├── core/             # 핵심 설정
│   │   ├── db/               # 데이터베이스 세션
│   │   ├── models/           # SQLAlchemy 모델
│   │   ├── modules/          # 비즈니스 로직 모듈
│   │   └── main.py           # FastAPI 애플리케이션
│   ├── alembic/              # 데이터베이스 마이그레이션
│   ├── tests/                # 테스트
│   └── requirements.txt      # Python 의존성
├── frontend/
│   ├── src/
│   │   ├── components/       # React 컴포넌트
│   │   ├── pages/            # 페이지 컴포넌트
│   │   ├── services/         # API 클라이언트
│   │   ├── types/            # TypeScript 타입
│   │   └── App.tsx           # 메인 앱
│   └── package.json          # Node.js 의존성
├── docs/                     # 설계 문서
├── docker/                   # Docker 설정
├── scripts/                  # 유틸리티 스크립트
└── docker-compose.yml        # Docker Compose 설정
```

## 🧪 테스트

### Backend 테스트
```bash
cd backend
pytest
pytest --cov=app tests/  # 커버리지 포함
```

### Frontend 테스트
```bash
cd frontend
npm test
```

## 🤝 기여하기

기여를 환영합니다! 다음 단계를 따라주세요:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

- [arXiv](https://arxiv.org/) - 오픈 액세스 논문 저장소
- [Semantic Scholar](https://www.semanticscholar.org/) - AI 기반 학술 검색 엔진
- [LightRAG](https://github.com/HKUDS/LightRAG) - 그래프 기반 RAG 프레임워크
- [FastAPI](https://fastapi.tiangolo.com/) - 현대적이고 빠른 Python 웹 프레임워크

## 📧 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 생성해주세요.

---

**Made with ❤️ for the AI research community**

# PaperPulse Backend

FastAPI 기반 백엔드 서버

## 개발 환경 설정

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements-dev.txt
```

### 3. 환경 변수 설정

```bash
cp ../.env.example ../.env
# .env 파일을 편집하여 필요한 설정 입력
```

### 4. 데이터베이스 설정

PostgreSQL이 실행 중이어야 합니다.

```bash
# pgvector 확장 설치 확인
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Alembic 마이그레이션 실행
alembic upgrade head
```

### 5. 개발 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 문서: http://localhost:8000/api/docs

## API 엔드포인트

### Papers

- `GET /api/v1/papers/` - 논문 목록 조회
- `GET /api/v1/papers/{paper_id}` - 논문 상세 조회
- `GET /api/v1/papers/arxiv/{arxiv_id}` - arXiv ID로 논문 조회
- `POST /api/v1/papers/` - 새 논문 생성
- `GET /api/v1/papers/stats/count` - 논문 통계

### Users

- `GET /api/v1/users/` - 사용자 목록 조회
- `GET /api/v1/users/{user_id}` - 사용자 상세 조회
- `POST /api/v1/users/` - 새 사용자 생성

## 테스트

```bash
pytest
pytest --cov=app tests/  # 커버리지 포함
```

## 코드 포맷팅

```bash
black app/
isort app/
flake8 app/
```

## 데이터베이스 마이그레이션

### 새 마이그레이션 생성

```bash
alembic revision --autogenerate -m "migration message"
```

### 마이그레이션 적용

```bash
alembic upgrade head
```

### 마이그레이션 롤백

```bash
alembic downgrade -1
```

## 프로젝트 구조

```
app/
├── api/
│   ├── routes/         # API 라우터
│   └── schemas/        # Pydantic 스키마
├── core/
│   ├── config.py       # 설정
│   └── logging.py      # 로깅 설정
├── db/
│   ├── base.py         # Base 클래스
│   └── session.py      # 데이터베이스 세션
├── models/             # SQLAlchemy 모델
├── modules/            # 비즈니스 로직 모듈
│   ├── ingestion/      # 데이터 수집
│   ├── pdf_processing/ # PDF 처리
│   ├── embeddings/     # 임베딩 생성
│   ├── knowledge_graph/# 지식 그래프
│   ├── search/         # 검색
│   └── notifications/  # 알림
└── main.py            # 메인 애플리케이션
```

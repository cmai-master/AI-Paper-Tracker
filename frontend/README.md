# PaperPulse Frontend

React + TypeScript 기반 프론트엔드 애플리케이션

## 개발 환경 설정

### 1. 의존성 설치

```bash
npm install
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 API URL 설정
```

### 3. 개발 서버 실행

```bash
npm run dev
```

애플리케이션: http://localhost:3000

## 빌드

### 프로덕션 빌드

```bash
npm run build
```

### 빌드 미리보기

```bash
npm run preview
```

## 테스트

```bash
npm test
```

## 코드 린팅

```bash
npm run lint
```

## 프로젝트 구조

```
src/
├── components/     # 재사용 가능한 컴포넌트
├── pages/          # 페이지 컴포넌트
├── services/       # API 클라이언트 및 서비스
├── hooks/          # 커스텀 React 훅
├── types/          # TypeScript 타입 정의
├── utils/          # 유틸리티 함수
├── App.tsx         # 메인 앱 컴포넌트
└── main.tsx        # 엔트리 포인트
```

## 주요 라이브러리

- **React 18**: UI 라이브러리
- **TypeScript**: 타입 안전성
- **Vite**: 빌드 도구
- **React Router**: 라우팅
- **TanStack Query**: 서버 상태 관리
- **Tailwind CSS**: 스타일링
- **Axios**: HTTP 클라이언트

# Notification & Recommendation Module - 설계 문서

**모듈명:** Notification & Recommendation Engine
**버전:** 1.0
**작성일:** 2025-11-14
**담당:** User Experience Team

---

## 1. 모듈 개요

### 1.1 목적
사용자의 연구 관심사를 학습하고 맞춤형 논문 추천 및 실시간 알림 제공

### 1.2 핵심 기능
- 사용자 프로필 관리 및 관심사 학습
- 다중 채널 알림 (Email, Slack, Push)
- 개인화 논문 추천
- 트렌드 기반 알림

---

## 2. 데이터 모델

### 2.1 사용자 프로필

```sql
-- 사용자 프로필
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200),

    -- 관심 키워드
    keywords TEXT[],

    -- 관심 카테고리
    categories TEXT[],  -- ["cs.AI", "cs.CL"]

    -- 팔로우 저자
    followed_authors TEXT[],

    -- 관심사 임베딩 (평균 벡터)
    interest_embedding VECTOR(1024),

    -- 알림 설정
    notification_settings JSONB,  -- {channels, frequency, min_score}

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 사용자 상호작용
CREATE TABLE user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) REFERENCES user_profiles(user_id),
    paper_id UUID REFERENCES papers(id),

    interaction_type VARCHAR(20),  -- view, bookmark, rate, click
    rating INT,  -- 1-5

    created_at TIMESTAMP DEFAULT NOW()
);

-- 추천 기록
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),
    paper_id UUID REFERENCES papers(id),

    relevance_score FLOAT,
    recommendation_reason TEXT,
    strategy VARCHAR(50),  -- collaborative, content, knowledge

    clicked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 알림 로그
CREATE TABLE notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100),
    paper_id UUID REFERENCES papers(id),

    channel VARCHAR(20),  -- email, slack, push
    status VARCHAR(20),  -- sent, failed, opened

    sent_at TIMESTAMP,
    opened_at TIMESTAMP
);
```

### 2.2 내부 모델

```python
from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    PUSH = "push"

class NotificationFrequency(str, Enum):
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"

class NotificationSettings(BaseModel):
    channels: List[NotificationChannel]
    frequency: NotificationFrequency
    min_relevance_score: float = 0.7
    quiet_hours: tuple[int, int] = (22, 8)  # 10PM - 8AM

class UserProfile(BaseModel):
    user_id: str
    email: Optional[str]
    keywords: List[str] = []
    categories: List[str] = []
    followed_authors: List[str] = []
    interest_embedding: Optional[List[float]]
    notification_settings: NotificationSettings

class RecommendationResult(BaseModel):
    paper_id: str
    title: str
    relevance_score: float
    reason: str
    strategy: str
```

---

## 3. 관련성 점수 계산

### 3.1 Relevance Scorer

```python
class RelevanceScorer:
    """사용자-논문 관련성 점수"""

    def calculate_score(
        self,
        paper: Paper,
        user: UserProfile,
        embedder: BGEM3Embedder
    ) -> float:
        """관련성 점수 계산 (0.0 - 1.0)"""

        scores = []
        weights = []

        # 1. 시맨틱 유사도 (40%)
        if user.interest_embedding and paper.document_embedding:
            semantic_score = cosine_similarity(
                paper.document_embedding,
                user.interest_embedding
            )
            scores.append(semantic_score)
            weights.append(0.4)

        # 2. 키워드 매칭 (25%)
        keyword_score = self._keyword_match(paper, user.keywords)
        scores.append(keyword_score)
        weights.append(0.25)

        # 3. 저자 팔로우 (15%)
        author_score = 1.0 if any(
            a.name in user.followed_authors for a in paper.authors
        ) else 0.0
        scores.append(author_score)
        weights.append(0.15)

        # 4. 카테고리 매칭 (10%)
        category_score = len(
            set(paper.categories) & set(user.categories)
        ) / max(len(user.categories), 1)
        scores.append(category_score)
        weights.append(0.1)

        # 5. 최신성 & 트렌드 (10%)
        recency_score = self._recency_score(paper)
        scores.append(recency_score)
        weights.append(0.1)

        final_score = sum(s * w for s, w in zip(scores, weights))
        return final_score

    def _keyword_match(self, paper: Paper, keywords: List[str]) -> float:
        """키워드 매칭"""
        text = f"{paper.title} {paper.abstract}".lower()
        matches = sum(1 for kw in keywords if kw.lower() in text)
        return min(matches / max(len(keywords), 1), 1.0)

    def _recency_score(self, paper: Paper) -> float:
        """최신성 점수"""
        days_old = (datetime.utcnow() - paper.published_at).days

        if days_old <= 1:
            return 1.0
        elif days_old <= 7:
            return 0.8
        elif days_old <= 30:
            return 0.5
        else:
            return 0.2
```

---

## 4. 추천 엔진

### 4.1 Multi-Strategy Recommender

```python
class RecommendationEngine:
    """하이브리드 추천 엔진"""

    def __init__(self, db: Session):
        self.db = db
        self.relevance_scorer = RelevanceScorer()

    def get_recommendations(
        self,
        user: UserProfile,
        n: int = 10
    ) -> List[RecommendationResult]:
        """추천 논문 생성"""

        # 1. Content-based (관심사 기반)
        content_recs = self._content_based_recommendations(user, n * 2)

        # 2. Collaborative filtering (유사 사용자 기반)
        collab_recs = self._collaborative_filtering(user, n * 2)

        # 3. Knowledge-aware (연구 경로 기반)
        knowledge_recs = self._knowledge_based_recommendations(user, n * 2)

        # 4. Combine with weights
        combined = self._combine_recommendations([
            (content_recs, 0.4),
            (collab_recs, 0.3),
            (knowledge_recs, 0.3)
        ])

        # 5. Diversity optimization
        diverse = self._optimize_diversity(combined, n)

        return diverse[:n]

    def _content_based_recommendations(
        self,
        user: UserProfile,
        n: int
    ) -> List[RecommendationResult]:
        """콘텐츠 기반 추천"""

        # 최근 7일 논문 중 관련성 높은 것
        recent_papers = self.db.query(Paper).filter(
            Paper.published_at >= datetime.utcnow() - timedelta(days=7)
        ).all()

        scored_papers = []
        for paper in recent_papers:
            score = self.relevance_scorer.calculate_score(paper, user)
            if score >= user.notification_settings.min_relevance_score:
                scored_papers.append((paper, score))

        # 점수 순 정렬
        scored_papers.sort(key=lambda x: x[1], reverse=True)

        return [
            RecommendationResult(
                paper_id=paper.id,
                title=paper.title,
                relevance_score=score,
                reason=f"Matches your interests in {', '.join(user.keywords[:3])}",
                strategy="content_based"
            )
            for paper, score in scored_papers[:n]
        ]

    def _collaborative_filtering(
        self,
        user: UserProfile,
        n: int
    ) -> List[RecommendationResult]:
        """협업 필터링"""

        # 유사한 사용자 찾기
        similar_users = self._find_similar_users(user, k=20)

        # 그들이 읽은 논문
        paper_scores = defaultdict(float)
        for similar_user, similarity in similar_users:
            interactions = self.db.query(UserInteraction).filter(
                UserInteraction.user_id == similar_user.user_id,
                UserInteraction.interaction_type.in_(['view', 'bookmark'])
            ).all()

            for interaction in interactions:
                paper_scores[interaction.paper_id] += similarity

        # 정렬
        sorted_papers = sorted(
            paper_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]

        return [
            RecommendationResult(
                paper_id=paper_id,
                title=self.db.query(Paper).get(paper_id).title,
                relevance_score=score,
                reason="Recommended by users with similar interests",
                strategy="collaborative"
            )
            for paper_id, score in sorted_papers
        ]

    def _optimize_diversity(
        self,
        papers: List[RecommendationResult],
        target: int
    ) -> List[RecommendationResult]:
        """다양성 최적화 (MMR)"""

        if len(papers) <= target:
            return papers

        selected = [papers[0]]
        remaining = papers[1:]

        while len(selected) < target and remaining:
            best_score = -1
            best_paper = None

            for paper in remaining:
                # Relevance
                relevance = paper.relevance_score

                # Diversity (기존 선택과의 차이)
                max_similarity = max(
                    self._topic_similarity(paper, s)
                    for s in selected
                )
                diversity = 1 - max_similarity

                # MMR score
                mmr = 0.6 * relevance + 0.4 * diversity

                if mmr > best_score:
                    best_score = mmr
                    best_paper = paper

            if best_paper:
                selected.append(best_paper)
                remaining.remove(best_paper)

        return selected
```

---

## 5. 알림 시스템

### 5.1 Notification Dispatcher

```python
class NotificationDispatcher:
    """알림 전송"""

    def __init__(self):
        self.email_service = EmailService()
        self.slack_service = SlackService()
        self.push_service = PushService()

    async def dispatch(
        self,
        user: UserProfile,
        paper: Paper,
        relevance_score: float
    ):
        """알림 전송"""

        # 최소 점수 체크
        if relevance_score < user.notification_settings.min_relevance_score:
            return

        # Quiet hours 체크
        current_hour = datetime.now().hour
        quiet_start, quiet_end = user.notification_settings.quiet_hours
        if quiet_start <= current_hour < quiet_end:
            # Queue for later
            await self._queue_notification(user, paper)
            return

        # 메시지 포맷
        message = self._format_notification(paper, relevance_score)

        # 채널별 전송
        for channel in user.notification_settings.channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    await self.email_service.send(user.email, message)
                elif channel == NotificationChannel.SLACK:
                    await self.slack_service.send(user.slack_webhook, message)
                elif channel == NotificationChannel.PUSH:
                    await self.push_service.send(user.user_id, message)

                # 로그 기록
                self._log_notification(user.user_id, paper.id, channel, "sent")

            except Exception as e:
                logger.error(f"Notification failed: {channel} - {e}")
                self._log_notification(user.user_id, paper.id, channel, "failed")

    def _format_notification(
        self,
        paper: Paper,
        score: float
    ) -> Dict:
        """알림 메시지 포맷"""
        return {
            "title": f"🔬 New Paper: {paper.title[:60]}...",
            "relevance": f"{score*100:.0f}%",
            "authors": ", ".join([a.name for a in paper.authors[:3]]),
            "abstract": paper.abstract[:200] + "...",
            "url": f"https://arxiv.org/abs/{paper.arxiv_id}",
            "actions": [
                {"label": "Read", "url": paper.pdf_url},
                {"label": "Bookmark", "action": "bookmark"},
                {"label": "Similar", "action": "find_similar"}
            ]
        }

class EmailService:
    """이메일 전송"""

    async def send(self, to_email: str, message: Dict):
        """이메일 전송"""
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = "noreply@paperpulse.ai"
        msg["To"] = to_email
        msg["Subject"] = message["title"]

        # HTML 템플릿
        html = f"""
        <h2>{message['title']}</h2>
        <p><strong>Relevance:</strong> {message['relevance']}</p>
        <p><strong>Authors:</strong> {message['authors']}</p>
        <p>{message['abstract']}</p>
        <p><a href="{message['url']}">Read Paper</a></p>
        """

        msg.set_content(html, subtype='html')

        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True
        )

class SlackService:
    """Slack 전송"""

    async def send(self, webhook_url: str, message: Dict):
        """Slack 전송"""
        import aiohttp

        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{message['title']}*\n_{message['authors']}_"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Relevance: {message['relevance']}\n\n{message['abstract']}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": action["label"]},
                            "url": action.get("url", "")
                        }
                        for action in message["actions"]
                    ]
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=payload)
```

---

## 6. API 엔드포인트

```python
@router.post("/users/profile")
async def create_user_profile(
    profile: UserProfile,
    db: Session = Depends(get_db)
):
    """사용자 프로필 생성"""
    db_profile = UserProfileModel(**profile.dict())
    db.add(db_profile)
    db.commit()
    return {"status": "created", "user_id": profile.user_id}

@router.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """추천 논문 조회"""
    user = db.query(UserProfileModel).filter_by(user_id=user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    engine = RecommendationEngine(db)
    recommendations = engine.get_recommendations(user, limit)

    return {"recommendations": recommendations}

@router.post("/interactions")
async def log_interaction(
    user_id: str,
    paper_id: str,
    interaction_type: str,
    rating: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """사용자 상호작용 기록"""
    interaction = UserInteraction(
        user_id=user_id,
        paper_id=paper_id,
        interaction_type=interaction_type,
        rating=rating
    )
    db.add(interaction)
    db.commit()

    # 관심사 임베딩 업데이트
    if interaction_type in ['bookmark', 'rate'] and rating >= 4:
        update_interest_embedding(user_id, paper_id)

    return {"status": "logged"}
```

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14

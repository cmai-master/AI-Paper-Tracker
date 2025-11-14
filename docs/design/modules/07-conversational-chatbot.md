# Conversational Chatbot Module - 설계 문서

**모듈명:** Conversational Chatbot Interface
**버전:** 1.0
**작성일:** 2025-11-14
**담당:** User Interface & Interaction Team

---

## 1. 모듈 개요

### 1.1 목적
자연스러운 대화를 통해 논문 검색, 질의응답, 추천, 트렌드 분석 등 모든 시스템 기능에 접근할 수 있는 대화형 인터페이스 제공

### 1.2 핵심 기능
- 멀티턴 대화 관리 및 컨텍스트 유지
- 의도 분류 및 엔티티 추출
- 다양한 작업 타입 지원 (검색, QA, 추천, 비교, 트렌드)
- 실시간 양방향 통신 (WebSocket)
- 대화 히스토리 관리 및 세션 유지
- 개인화된 응답 생성

### 1.3 주요 사용 사례

**시나리오 1: 논문 검색**
```
User: "최근 Retrieval Augmented Generation에 관한 논문을 찾아줘"
Bot: "RAG 관련 최신 논문을 검색했습니다. 2024-2025년 사이 12개의 논문을 찾았어요."
     [논문 리스트 + 요약]
User: "이 중에서 가장 인용이 많은 논문은?"
Bot: [컨텍스트 기반으로 앞서 검색한 결과에서 필터링]
```

**시나리오 2: 질의응답**
```
User: "Transformer의 attention mechanism이 뭐야?"
Bot: [관련 논문에서 정보를 추출하여 답변 + 인용]
User: "그럼 이게 RNN보다 나은 점은?"
Bot: [이전 대화 컨텍스트를 유지하며 비교 분석]
```

**시나리오 3: 추천**
```
User: "내 관심사에 맞는 새 논문 있어?"
Bot: [사용자 프로필 기반 추천 + 이유 설명]
```

---

## 2. 시스템 아키텍처

### 2.1 Chatbot Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │          React Chat UI Component                  │   │
│  │  - Message display                                │   │
│  │  - Input handling                                 │   │
│  │  - Typing indicators                              │   │
│  │  - Rich media rendering (papers, charts)         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         ▲ ▼ WebSocket
┌─────────────────────────────────────────────────────────┐
│                  WebSocket Gateway                       │
│  - Connection management                                 │
│  - Authentication                                        │
│  - Message routing                                       │
└─────────────────────────────────────────────────────────┘
                         ▲ ▼
┌─────────────────────────────────────────────────────────┐
│              Conversation Manager                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │          LangGraph Chatbot Agent                  │   │
│  │                                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │   │
│  │  │   Intent    │→ │   Router    │→ │ Response │ │   │
│  │  │ Classifier  │  │   Agent     │  │Generator │ │   │
│  │  └─────────────┘  └─────────────┘  └──────────┘ │   │
│  │          ▲              │                         │   │
│  │          │              ▼                         │   │
│  │  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │  Context    │  │Task Agents  │               │   │
│  │  │  Manager    │  │- Search     │               │   │
│  │  │             │  │- QA         │               │   │
│  │  └─────────────┘  │- Recommend  │               │   │
│  │                    │- Compare    │               │   │
│  │                    └─────────────┘               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         ▲ ▼
┌─────────────────────────────────────────────────────────┐
│                  Backend Services                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  Search  │  │    QA    │  │Knowledge │             │
│  │  Service │  │  Engine  │  │  Graph   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                         ▲ ▼
┌─────────────────────────────────────────────────────────┐
│                     Data Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │PostgreSQL│  │  Redis   │  │   S3     │             │
│  │(Sessions)│  │ (Cache)  │  │(History) │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 대화 관리 시스템

### 3.1 LangGraph Agent 구조

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator

class ConversationState(TypedDict):
    """대화 상태"""
    messages: Annotated[Sequence[dict], operator.add]
    user_id: str
    session_id: str
    context: dict  # 이전 대화 컨텍스트
    current_intent: str
    entities: dict
    task_results: dict

class ChatbotAgent:
    """LangGraph 기반 챗봇 Agent"""

    def __init__(self, db: Session):
        self.db = db
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """대화 흐름 그래프 구성"""
        workflow = StateGraph(ConversationState)

        # 노드 추가
        workflow.add_node("analyze_intent", self.analyze_intent)
        workflow.add_node("load_context", self.load_context)
        workflow.add_node("route_task", self.route_task)
        workflow.add_node("execute_search", self.execute_search)
        workflow.add_node("execute_qa", self.execute_qa)
        workflow.add_node("execute_recommend", self.execute_recommend)
        workflow.add_node("execute_compare", self.execute_compare)
        workflow.add_node("generate_response", self.generate_response)
        workflow.add_node("save_context", self.save_context)

        # 엣지 정의
        workflow.set_entry_point("analyze_intent")

        workflow.add_edge("analyze_intent", "load_context")
        workflow.add_edge("load_context", "route_task")

        # 조건부 라우팅
        workflow.add_conditional_edges(
            "route_task",
            self.decide_task_type,
            {
                "search": "execute_search",
                "qa": "execute_qa",
                "recommend": "execute_recommend",
                "compare": "execute_compare",
                "chitchat": "generate_response"
            }
        )

        # 모든 태스크 실행 후 응답 생성으로
        for task_node in ["execute_search", "execute_qa", "execute_recommend", "execute_compare"]:
            workflow.add_edge(task_node, "generate_response")

        workflow.add_edge("generate_response", "save_context")
        workflow.add_edge("save_context", END)

        return workflow.compile()

    async def analyze_intent(self, state: ConversationState) -> ConversationState:
        """의도 분석"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI()

        last_message = state["messages"][-1]["content"]

        # Few-shot prompt for intent classification
        prompt = f"""Analyze the user's intent in this research assistant conversation.

Previous context: {state.get('context', {})}

User message: {last_message}

Classify into one of:
- search: Finding papers
- qa: Answering questions about concepts/papers
- recommend: Getting paper recommendations
- compare: Comparing papers/methods/concepts
- chitchat: General conversation

Extract entities (paper titles, concepts, authors, years, etc.)

Respond in JSON format:
{{"intent": "...", "entities": {{}}, "needs_context": true/false}}
"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        import json
        analysis = json.loads(response.choices[0].message.content)

        state["current_intent"] = analysis["intent"]
        state["entities"] = analysis.get("entities", {})

        return state

    async def load_context(self, state: ConversationState) -> ConversationState:
        """이전 대화 컨텍스트 로드"""
        session_id = state["session_id"]

        # Redis에서 세션 컨텍스트 가져오기
        import redis
        r = redis.Redis()

        context_key = f"chat_context:{session_id}"
        context_data = r.get(context_key)

        if context_data:
            state["context"] = json.loads(context_data)
        else:
            state["context"] = {}

        return state

    def decide_task_type(self, state: ConversationState) -> str:
        """태스크 타입 결정"""
        return state["current_intent"]

    async def execute_search(self, state: ConversationState) -> ConversationState:
        """검색 실행"""
        from services.search import SearchService

        query = state["messages"][-1]["content"]
        search_service = SearchService(self.db)

        # 엔티티에서 필터 추출
        filters = self._extract_filters(state["entities"])

        results = await search_service.search(
            query=query,
            mode="hybrid",
            top_k=5,
            filters=filters
        )

        state["task_results"] = {
            "type": "search",
            "results": results
        }

        return state

    async def execute_qa(self, state: ConversationState) -> ConversationState:
        """QA 실행"""
        from services.qa import QAEngine

        question = state["messages"][-1]["content"]
        qa_engine = QAEngine(self.db)

        answer = await qa_engine.answer_question(question)

        state["task_results"] = {
            "type": "qa",
            "answer": answer
        }

        return state

    async def execute_recommend(self, state: ConversationState) -> ConversationState:
        """추천 실행"""
        from services.recommendation import RecommendationService

        user_id = state["user_id"]
        rec_service = RecommendationService(self.db)

        recommendations = await rec_service.get_personalized_recommendations(
            user_id=user_id,
            limit=5
        )

        state["task_results"] = {
            "type": "recommend",
            "recommendations": recommendations
        }

        return state

    async def execute_compare(self, state: ConversationState) -> ConversationState:
        """비교 실행"""
        from services.comparison import ComparisonEngine

        entities = state["entities"].get("compare_entities", [])
        comparison_engine = ComparisonEngine(self.db)

        result = await comparison_engine.compare(entities)

        state["task_results"] = {
            "type": "compare",
            "comparison": result
        }

        return state

    async def generate_response(self, state: ConversationState) -> ConversationState:
        """응답 생성"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI()

        # 태스크 결과를 자연스러운 응답으로 변환
        task_results = state.get("task_results", {})

        if task_results:
            response_prompt = self._build_response_prompt(
                state["messages"][-1]["content"],
                task_results,
                state["context"]
            )
        else:
            # Chitchat
            response_prompt = f"""You are a helpful research assistant.

User message: {state["messages"][-1]["content"]}

Respond naturally and helpfully."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": response_prompt}]
        )

        bot_message = response.choices[0].message.content

        state["messages"].append({
            "role": "assistant",
            "content": bot_message,
            "metadata": task_results
        })

        return state

    async def save_context(self, state: ConversationState) -> ConversationState:
        """컨텍스트 저장"""
        import redis
        r = redis.Redis()

        # 최근 대화와 결과를 컨텍스트에 저장
        context = {
            "last_intent": state["current_intent"],
            "last_entities": state["entities"],
            "last_results": state.get("task_results", {}),
            "recent_messages": state["messages"][-5:]  # 최근 5개 메시지
        }

        context_key = f"chat_context:{state['session_id']}"
        r.setex(context_key, 3600, json.dumps(context))  # 1시간 TTL

        return state

    def _build_response_prompt(
        self,
        user_message: str,
        task_results: dict,
        context: dict
    ) -> str:
        """응답 생성 프롬프트"""

        result_type = task_results.get("type")

        if result_type == "search":
            papers = task_results["results"]["papers"]
            return f"""User asked: {user_message}

Search results:
{json.dumps(papers, indent=2)}

Generate a natural, conversational response that:
1. Summarizes how many papers were found
2. Highlights 2-3 most relevant papers with brief descriptions
3. Asks if they want more details or to refine the search
"""

        elif result_type == "qa":
            answer = task_results["answer"]
            return f"""User asked: {user_message}

Answer with citations:
{answer["answer"]}

Sources: {answer["citations"]}

Reformat this into a natural conversational response that maintains citations.
"""

        elif result_type == "recommend":
            recs = task_results["recommendations"]
            return f"""User asked for recommendations.

Recommended papers:
{json.dumps(recs, indent=2)}

Generate a friendly response explaining why these papers are recommended based on their interests.
"""

        elif result_type == "compare":
            comparison = task_results["comparison"]
            return f"""User asked to compare: {user_message}

Comparison results:
{comparison}

Present this comparison in a clear, structured way.
"""

        return user_message
```

---

## 4. WebSocket 통신

### 4.1 WebSocket Manager

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json
import asyncio

class ConnectionManager:
    """WebSocket 연결 관리"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """연결 수락"""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        """연결 해제"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict):
        """메시지 전송"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)

    async def send_typing_indicator(self, session_id: str, is_typing: bool):
        """타이핑 인디케이터"""
        await self.send_message(session_id, {
            "type": "typing",
            "is_typing": is_typing
        })

    async def send_streaming_response(self, session_id: str, chunks: list):
        """스트리밍 응답 (토큰 단위)"""
        for chunk in chunks:
            await self.send_message(session_id, {
                "type": "stream",
                "content": chunk
            })
            await asyncio.sleep(0.05)  # 자연스러운 타이핑 효과

manager = ConnectionManager()

@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(...)
):
    """WebSocket 엔드포인트"""
    await manager.connect(session_id, websocket)

    # 챗봇 에이전트 초기화
    chatbot = ChatbotAgent(db=get_db())

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "message":
                # 타이핑 인디케이터 표시
                await manager.send_typing_indicator(session_id, True)

                # 대화 상태 구성
                state = ConversationState(
                    messages=[{"role": "user", "content": data["content"]}],
                    user_id=user_id,
                    session_id=session_id,
                    context={},
                    current_intent="",
                    entities={},
                    task_results={}
                )

                # LangGraph agent 실행
                result = await chatbot.graph.ainvoke(state)

                # 타이핑 인디케이터 숨기기
                await manager.send_typing_indicator(session_id, False)

                # 응답 전송
                bot_message = result["messages"][-1]
                await manager.send_message(session_id, {
                    "type": "message",
                    "content": bot_message["content"],
                    "metadata": bot_message.get("metadata", {})
                })

                # 대화 히스토리 저장
                await save_chat_history(
                    session_id,
                    user_id,
                    data["content"],
                    bot_message["content"]
                )

            elif message_type == "feedback":
                # 사용자 피드백 (좋아요/싫어요)
                await handle_feedback(
                    session_id,
                    data["message_id"],
                    data["feedback"]
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

---

## 5. 세션 및 히스토리 관리

### 5.1 Chat Session Model

```python
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid

class ChatSession(Base):
    """채팅 세션"""
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = Column(String(255))  # 자동 생성된 대화 제목
    metadata = Column(JSON)  # 추가 정보

class ChatMessage(Base):
    """채팅 메시지"""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 추가 메타데이터
    intent = Column(String(50))
    entities = Column(JSON)
    task_results = Column(JSON)  # 검색결과, QA 답변 등

    # 사용자 피드백
    feedback = Column(Integer)  # 1: 좋아요, -1: 싫어요, null: 없음

async def save_chat_history(
    session_id: str,
    user_id: str,
    user_message: str,
    bot_message: str
):
    """대화 히스토리 저장"""

    # 세션이 없으면 생성
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        session = ChatSession(
            id=session_id,
            user_id=user_id,
            title=await generate_session_title(user_message)
        )
        db.add(session)

    # 메시지 저장
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=user_message
    )

    bot_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=bot_message
    )

    db.add_all([user_msg, bot_msg])
    db.commit()

async def generate_session_title(first_message: str) -> str:
    """첫 메시지로부터 세션 제목 생성"""
    from openai import AsyncOpenAI

    client = AsyncOpenAI()

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"Generate a short (3-5 words) title for a conversation starting with: {first_message}"
        }]
    )

    return response.choices[0].message.content
```

---

## 6. 고급 기능

### 6.1 멀티모달 응답

```python
class ResponseFormatter:
    """응답 포맷팅 (Rich UI 요소)"""

    def format_paper_card(self, paper: dict) -> dict:
        """논문 카드 형식"""
        return {
            "type": "paper_card",
            "data": {
                "title": paper["title"],
                "authors": paper["authors"],
                "abstract": paper["abstract"][:200] + "...",
                "arxiv_id": paper["arxiv_id"],
                "published_date": paper["published_at"],
                "citations": paper.get("citation_count", 0),
                "url": f"https://arxiv.org/abs/{paper['arxiv_id']}",
                "thumbnail": paper.get("thumbnail_url")
            }
        }

    def format_comparison_table(self, comparison: dict) -> dict:
        """비교 테이블"""
        return {
            "type": "comparison_table",
            "data": {
                "entities": comparison["entities"],
                "aspects": comparison["aspects"],
                "table": comparison["comparison_table"]
            }
        }

    def format_trend_chart(self, trend: dict) -> dict:
        """트렌드 차트"""
        return {
            "type": "trend_chart",
            "data": {
                "concept": trend["concept"],
                "chart_data": {
                    "labels": list(trend["yearly_counts"].keys()),
                    "values": list(trend["yearly_counts"].values())
                },
                "growth_rate": trend["growth_rate"],
                "direction": trend["trend_direction"]
            }
        }
```

### 6.2 개인화 및 학습

```python
class PersonalizationEngine:
    """사용자 개인화"""

    def __init__(self, db: Session):
        self.db = db

    async def learn_from_interaction(
        self,
        user_id: str,
        message: ChatMessage,
        feedback: int
    ):
        """상호작용으로부터 학습"""

        # 긍정적 피드백
        if feedback > 0:
            # 사용자 관심사 업데이트
            if message.entities:
                await self._update_user_interests(
                    user_id,
                    message.entities
                )

        # 부정적 피드백
        elif feedback < 0:
            # 응답 패턴 분석 및 개선
            await self._log_negative_feedback(
                user_id,
                message.intent,
                message.task_results
            )

    async def _update_user_interests(self, user_id: str, entities: dict):
        """사용자 관심사 업데이트"""
        from models.user import UserProfile

        profile = self.db.query(UserProfile).filter_by(user_id=user_id).first()

        if not profile:
            return

        # 엔티티를 관심 키워드에 추가
        current_interests = profile.interests or []

        for entity_type, entity_values in entities.items():
            if isinstance(entity_values, list):
                current_interests.extend(entity_values)
            else:
                current_interests.append(entity_values)

        # 중복 제거 및 상위 N개 유지
        profile.interests = list(set(current_interests))[:50]
        self.db.commit()
```

### 6.3 대화 분석 및 모니터링

```python
class ConversationAnalytics:
    """대화 분석"""

    def __init__(self, db: Session):
        self.db = db

    def get_session_metrics(self, session_id: str) -> dict:
        """세션 메트릭"""

        messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id
        ).all()

        return {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m.role == "user"]),
            "avg_response_time": self._calculate_avg_response_time(messages),
            "intents_distribution": self._get_intent_distribution(messages),
            "positive_feedback_rate": self._calculate_feedback_rate(messages, 1),
            "negative_feedback_rate": self._calculate_feedback_rate(messages, -1)
        }

    def get_user_conversation_stats(self, user_id: str) -> dict:
        """사용자 대화 통계"""

        sessions = self.db.query(ChatSession).filter_by(user_id=user_id).all()

        total_messages = sum(
            self.db.query(ChatMessage).filter_by(session_id=s.id).count()
            for s in sessions
        )

        return {
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "avg_messages_per_session": total_messages / len(sessions) if sessions else 0,
            "most_common_intents": self._get_top_intents(user_id)
        }
```

---

## 7. API 엔드포인트

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/sessions")
async def create_chat_session(
    user_id: str,
    db: Session = Depends(get_db)
):
    """새 채팅 세션 생성"""
    session = ChatSession(user_id=user_id)
    db.add(session)
    db.commit()

    return {"session_id": str(session.id)}

@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """채팅 세션 조회"""
    session = db.query(ChatSession).filter_by(id=session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session

@router.get("/sessions/{session_id}/messages")
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """채팅 히스토리 조회"""
    messages = db.query(ChatMessage).filter_by(
        session_id=session_id
    ).order_by(
        ChatMessage.created_at.desc()
    ).limit(limit).offset(offset).all()

    return {
        "messages": messages,
        "total": db.query(ChatMessage).filter_by(session_id=session_id).count()
    }

@router.get("/sessions")
async def list_user_sessions(
    user_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """사용자의 채팅 세션 목록"""
    sessions = db.query(ChatSession).filter_by(
        user_id=user_id
    ).order_by(
        ChatSession.updated_at.desc()
    ).limit(limit).all()

    return {"sessions": sessions}

@router.post("/messages/{message_id}/feedback")
async def submit_feedback(
    message_id: str,
    feedback: int,  # 1 or -1
    db: Session = Depends(get_db)
):
    """메시지 피드백 제출"""
    message = db.query(ChatMessage).filter_by(id=message_id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.feedback = feedback
    db.commit()

    # 개인화 학습
    personalization = PersonalizationEngine(db)
    await personalization.learn_from_interaction(
        message.session.user_id,
        message,
        feedback
    )

    return {"status": "success"}

@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """채팅 세션 삭제"""
    session = db.query(ChatSession).filter_by(id=session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 메시지도 함께 삭제 (CASCADE)
    db.delete(session)
    db.commit()

    return {"status": "deleted"}
```

---

## 8. Frontend 연동

### 8.1 React Chat Component Example

```typescript
// ChatInterface.tsx
import React, { useState, useEffect, useRef } from 'react';
import useWebSocket from 'react-use-websocket';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: any;
  timestamp: Date;
}

export const ChatInterface: React.FC<{ sessionId: string; userId: string }> = ({
  sessionId,
  userId,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const { sendJsonMessage, lastJsonMessage } = useWebSocket(
    `ws://localhost:8000/ws/chat/${sessionId}?user_id=${userId}`,
    {
      onOpen: () => console.log('Connected'),
      shouldReconnect: () => true,
    }
  );

  useEffect(() => {
    if (lastJsonMessage) {
      handleWebSocketMessage(lastJsonMessage);
    }
  }, [lastJsonMessage]);

  const handleWebSocketMessage = (message: any) => {
    if (message.type === 'typing') {
      setIsTyping(message.is_typing);
    } else if (message.type === 'message') {
      setMessages(prev => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: message.content,
          metadata: message.metadata,
          timestamp: new Date(),
        },
      ]);
      setIsTyping(false);
    }
  };

  const sendMessage = () => {
    if (!input.trim()) return;

    // Add user message to UI
    setMessages(prev => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'user',
        content: input,
        timestamp: new Date(),
      },
    ]);

    // Send to backend
    sendJsonMessage({
      type: 'message',
      content: input,
    });

    setInput('');
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>

      <div className="input-container">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about papers..."
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
};
```

---

## 9. 성능 최적화

### 9.1 캐싱 전략

```python
# 자주 묻는 질문 캐싱
@router.post("/chat/message")
@cache(expire=3600, key_builder=lambda *args, **kwargs: f"chat:{hash(kwargs['message'])}")
async def cached_chat_response(message: str):
    """캐시된 응답"""
    pass

# Context 압축
class ContextCompressor:
    """대화 컨텍스트 압축"""

    def compress_history(self, messages: List[dict], max_tokens: int = 1000) -> str:
        """히스토리를 요약하여 토큰 수 줄이기"""

        # 최근 N개 메시지만 유지
        recent = messages[-10:]

        # 오래된 메시지는 요약
        if len(messages) > 10:
            old_messages = messages[:-10]
            summary = self._summarize_messages(old_messages)
            return f"Previous conversation summary: {summary}\n\nRecent messages: {recent}"

        return str(recent)
```

### 9.2 부하 분산

```yaml
# 챗봇 워커 auto-scaling 설정
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: chatbot-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: chatbot-worker
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: websocket_connections
      target:
        type: AverageValue
        averageValue: "100"
```

---

## 10. 모니터링 및 로깅

### 10.1 메트릭

```python
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
chat_messages_total = Counter(
    'chat_messages_total',
    'Total chat messages',
    ['intent', 'status']
)

chat_response_time = Histogram(
    'chat_response_time_seconds',
    'Chat response time'
)

active_chat_sessions = Gauge(
    'active_chat_sessions',
    'Number of active chat sessions'
)

# 사용
@chat_endpoint
async def handle_chat():
    with chat_response_time.time():
        # Process message
        chat_messages_total.labels(intent='search', status='success').inc()
```

### 10.2 로깅

```python
import structlog

logger = structlog.get_logger()

@websocket_endpoint
async def chat_handler(websocket: WebSocket, session_id: str):
    logger.info(
        "chat_session_started",
        session_id=session_id,
        user_id=user_id
    )

    try:
        # Handle messages
        pass
    except Exception as e:
        logger.error(
            "chat_error",
            session_id=session_id,
            error=str(e),
            exc_info=True
        )
```

---

## 11. 보안 고려사항

### 11.1 입력 검증 및 Sanitization

```python
from bleach import clean

def sanitize_user_input(text: str) -> str:
    """사용자 입력 정화"""
    # HTML 태그 제거
    cleaned = clean(text, tags=[], strip=True)

    # 길이 제한
    if len(cleaned) > 2000:
        cleaned = cleaned[:2000]

    return cleaned

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.websocket("/ws/chat/{session_id}")
@limiter.limit("100/minute")
async def rate_limited_chat(websocket: WebSocket):
    pass
```

### 11.2 PII 보호

```python
import re

class PIIFilter:
    """개인정보 필터링"""

    def __init__(self):
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b'
        }

    def filter(self, text: str) -> str:
        """PII 제거"""
        for pii_type, pattern in self.patterns.items():
            text = re.sub(pattern, f'[{pii_type.upper()}_REDACTED]', text)
        return text
```

---

## 12. 테스트

### 12.1 단위 테스트

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_intent_classification():
    """의도 분류 테스트"""
    chatbot = ChatbotAgent(db=Mock())

    state = ConversationState(
        messages=[{"role": "user", "content": "Find papers about transformers"}],
        user_id="test_user",
        session_id="test_session",
        context={},
        current_intent="",
        entities={},
        task_results={}
    )

    result = await chatbot.analyze_intent(state)

    assert result["current_intent"] == "search"
    assert "transformers" in result["entities"]

@pytest.mark.asyncio
async def test_context_preservation():
    """컨텍스트 유지 테스트"""
    chatbot = ChatbotAgent(db=Mock())

    # 첫 번째 대화
    state1 = await chatbot.process_message("Find papers about RAG")

    # 두 번째 대화 (컨텍스트 참조)
    state2 = await chatbot.process_message("Show me the most cited one")

    assert state2["context"]["last_intent"] == "search"
```

---

## 13. 배포 및 확장

### 13.1 Docker Compose

```yaml
version: '3.8'

services:
  chatbot-api:
    build: ./chatbot
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://user:pass@db:5432/paperpulse
    depends_on:
      - redis
      - db
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 2G

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=paperpulse
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

---

**문서 버전:** 1.0
**최종 업데이트:** 2025-11-14
**다음 리뷰:** 2025-12-14

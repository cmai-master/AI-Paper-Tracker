"""
Conversation State Management
"""
from typing import List, Dict, Optional, TypedDict
from datetime import datetime


class Message(TypedDict):
    """Single message in conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[Dict]


class ConversationState(TypedDict):
    """
    State of a conversation
    Compatible with LangGraph state management
    """
    # Conversation history
    messages: List[Message]

    # Current user query
    query: str

    # User context
    user_id: Optional[str]
    user_interests: List[str]

    # Intermediate results
    search_results: Optional[List[Dict]]
    recommendations: Optional[List[Dict]]

    # Tool outputs
    tool_calls: List[Dict]
    tool_outputs: List[Dict]

    # Final response
    response: Optional[str]

    # Metadata
    session_id: str
    created_at: datetime
    last_updated: datetime


class ConversationMemory:
    """Manages conversation history and context"""

    def __init__(self, max_messages: int = 20):
        """
        Initialize conversation memory

        Args:
            max_messages: Maximum messages to keep in memory
        """
        self.max_messages = max_messages
        self.conversations: Dict[str, ConversationState] = {}

    def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        user_interests: List[str] = None
    ) -> ConversationState:
        """Create a new conversation session"""
        state: ConversationState = {
            "messages": [],
            "query": "",
            "user_id": user_id,
            "user_interests": user_interests or [],
            "search_results": None,
            "recommendations": None,
            "tool_calls": [],
            "tool_outputs": [],
            "response": None,
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow()
        }

        self.conversations[session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Get conversation session"""
        return self.conversations.get(session_id)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ):
        """Add a message to conversation"""
        state = self.conversations.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        message: Message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata
        }

        state["messages"].append(message)

        # Trim old messages if needed
        if len(state["messages"]) > self.max_messages:
            state["messages"] = state["messages"][-self.max_messages:]

        state["last_updated"] = datetime.utcnow()

    def get_history(
        self,
        session_id: str,
        limit: int = None
    ) -> List[Message]:
        """Get conversation history"""
        state = self.conversations.get(session_id)
        if not state:
            return []

        messages = state["messages"]
        if limit:
            messages = messages[-limit:]

        return messages

    def clear_session(self, session_id: str):
        """Clear a conversation session"""
        if session_id in self.conversations:
            del self.conversations[session_id]

    def get_context_summary(self, session_id: str) -> str:
        """Get a summary of conversation context"""
        state = self.conversations.get(session_id)
        if not state or not state["messages"]:
            return "No previous conversation"

        # Get last few messages
        recent = state["messages"][-5:]
        summary_parts = []

        for msg in recent:
            summary_parts.append(f"{msg['role']}: {msg['content'][:100]}...")

        return "\n".join(summary_parts)

"""
PaperPulse Chatbot Agent
LangGraph-based conversational agent for paper exploration
"""
import json
import logging
from typing import Dict, List, Optional

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .conversation_state import ConversationState, ConversationMemory
from .tools import SearchTool, RecommendTool, CompareTool, QATool, TrendTool

logger = logging.getLogger(__name__)


class PaperPulseChatbot:
    """Conversational chatbot for paper exploration"""

    def __init__(
        self,
        api_key: str = None,
        search_service=None,
        recommendation_engine=None,
        comparison_engine=None,
        qa_engine=None,
        trend_analyzer=None
    ):
        """Initialize chatbot"""
        self.api_key = api_key

        # Initialize LLM client
        if OPENAI_AVAILABLE and api_key:
            self.client = OpenAI(api_key=api_key)
            self.llm_available = True
        else:
            self.client = None
            self.llm_available = False
            logger.warning("OpenAI not available, chatbot will be limited")

        # Initialize tools
        self.tools = {}
        if search_service:
            self.tools["search"] = SearchTool(search_service)
        if recommendation_engine:
            self.tools["recommend"] = RecommendTool(recommendation_engine)
        if comparison_engine:
            self.tools["compare"] = CompareTool(comparison_engine)
        if qa_engine:
            self.tools["qa"] = QATool(qa_engine)
        if trend_analyzer:
            self.tools["trend"] = TrendTool(trend_analyzer)

        # Conversation memory
        self.memory = ConversationMemory()

        # Build LangGraph workflow if available
        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_graph()
        else:
            self.graph = None
            logger.warning("LangGraph not available, using fallback chatbot")

    def _build_graph(self) -> Optional['StateGraph']:
        """Build LangGraph workflow"""
        if not LANGGRAPH_AVAILABLE:
            return None

        # Create state graph
        workflow = StateGraph(ConversationState)

        # Define nodes
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("route_to_tool", self._route_to_tool)
        workflow.add_node("execute_tool", self._execute_tool)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges
        workflow.set_entry_point("analyze_intent")
        workflow.add_edge("analyze_intent", "route_to_tool")
        workflow.add_edge("route_to_tool", "execute_tool")
        workflow.add_edge("execute_tool", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    async def chat(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Process a chat query

        Args:
            query: User query
            session_id: Conversation session ID
            user_id: Optional user ID

        Returns:
            Assistant response
        """
        # Get or create session
        state = self.memory.get_session(session_id)
        if not state:
            state = self.memory.create_session(session_id, user_id)

        # Add user message
        self.memory.add_message(session_id, "user", query)

        # Update state with current query
        state["query"] = query

        # Use LangGraph if available, otherwise fallback
        if self.graph and LANGGRAPH_AVAILABLE:
            result = await self.graph.ainvoke(state)
            response = result.get("response", "I'm not sure how to help with that.")
        else:
            response = await self._fallback_chat(query, state)

        # Add assistant response to memory
        self.memory.add_message(session_id, "assistant", response)

        return response

    async def _fallback_chat(
        self,
        query: str,
        state: ConversationState
    ) -> str:
        """Fallback chat without LangGraph"""
        if not self.llm_available:
            return "Chatbot service not available - OpenAI API required"

        # Get conversation history
        history = self.memory.get_history(state["session_id"], limit=5)

        # Build prompt
        messages = [
            {
                "role": "system",
                "content": """You are PaperPulse, an AI assistant that helps researchers find and explore academic papers.
You can help with:
- Searching for papers on specific topics
- Recommending relevant papers
- Answering questions about research
- Comparing papers or techniques
- Analyzing research trends

Be helpful, concise, and provide specific information when possible."""
            }
        ]

        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add current query
        messages.append({
            "role": "user",
            "content": query
        })

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Fallback chat failed: {e}")
            return "I encountered an error processing your request. Please try again."

    async def _analyze_intent(self, state: ConversationState) -> ConversationState:
        """Analyze user intent"""
        query = state["query"]

        if not self.llm_available:
            state["metadata"] = {"intent": "unknown"}
            return state

        prompt = f"""Analyze the user's intent from this query:
"{query}"

Classify into one of these categories:
- search: User wants to find papers
- recommend: User wants recommendations
- qa: User has a specific question to answer
- compare: User wants to compare papers/techniques
- trend: User wants to understand trends
- chat: General conversation

Respond with just the category name."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.3
            )

            intent = response.choices[0].message.content.strip().lower()
            state["metadata"] = {"intent": intent}

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            state["metadata"] = {"intent": "chat"}

        return state

    async def _route_to_tool(self, state: ConversationState) -> ConversationState:
        """Route to appropriate tool based on intent"""
        intent = state.get("metadata", {}).get("intent", "chat")

        tool_mapping = {
            "search": "search",
            "recommend": "recommend",
            "qa": "qa",
            "compare": "compare",
            "trend": "trend"
        }

        tool_name = tool_mapping.get(intent)
        if tool_name and tool_name in self.tools:
            state["metadata"]["tool"] = tool_name
        else:
            state["metadata"]["tool"] = None

        return state

    async def _execute_tool(self, state: ConversationState) -> ConversationState:
        """Execute the selected tool"""
        tool_name = state.get("metadata", {}).get("tool")

        if not tool_name or tool_name not in self.tools:
            return state

        tool = self.tools[tool_name]
        query = state["query"]

        try:
            # Execute tool based on type
            if tool_name == "search":
                result = await tool.run(query=query, top_k=10)
                state["search_results"] = result.get("papers", [])

            elif tool_name == "recommend":
                user_id = state.get("user_id", "default")
                result = await tool.run(user_id=user_id, n=10)
                state["recommendations"] = result.get("recommendations", [])

            elif tool_name == "qa":
                result = await tool.run(question=query)
                state["metadata"]["qa_result"] = result

            elif tool_name == "compare":
                # Extract entities from query (simplified)
                entities = self._extract_entities_from_query(query)
                result = await tool.run(entities=entities)
                state["metadata"]["comparison_result"] = result

            elif tool_name == "trend":
                # Extract concept from query
                concept = query.replace("trend", "").replace("evolution", "").strip()
                result = await tool.run(concept=concept)
                state["metadata"]["trend_result"] = result

            # Record tool execution
            state["tool_calls"].append({
                "tool": tool_name,
                "query": query,
                "timestamp": str(state["last_updated"])
            })

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            state["metadata"]["tool_error"] = str(e)

        return state

    async def _generate_response(self, state: ConversationState) -> ConversationState:
        """Generate final response"""
        if not self.llm_available:
            state["response"] = "Response generation not available"
            return state

        # Build context from tool outputs
        context_parts = []

        if state.get("search_results"):
            context_parts.append(
                f"Search found {len(state['search_results'])} papers"
            )

        if state.get("recommendations"):
            context_parts.append(
                f"Generated {len(state['recommendations'])} recommendations"
            )

        metadata = state.get("metadata", {})
        if "qa_result" in metadata:
            qa_result = metadata["qa_result"]
            context_parts.append(f"QA Answer: {qa_result.get('answer', '')}")

        if "comparison_result" in metadata:
            comp_result = metadata["comparison_result"]
            context_parts.append(f"Comparison: {comp_result.get('summary', '')}")

        if "trend_result" in metadata:
            trend_result = metadata["trend_result"]
            context_parts.append(
                f"Trend: {trend_result.get('trend_direction', '')} "
                f"(growth: {trend_result.get('growth_rate', 0):.1%})"
            )

        context = "\n".join(context_parts) if context_parts else "No specific results"

        # Generate response
        prompt = f"""User query: {state['query']}

Context from tools:
{context}

Generate a helpful, concise response to the user. Include specific information from the context.
If papers were found, mention them. If analysis was done, explain the findings."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7
            )

            state["response"] = response.choices[0].message.content

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            state["response"] = "I encountered an error generating a response."

        return state

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """Simple entity extraction from query"""
        # This is a simplified version - would use NER in production
        words = query.split()

        # Look for capitalized phrases or quoted text
        entities = []

        # Find quoted text
        import re
        quoted = re.findall(r'"([^"]*)"', query)
        entities.extend(quoted)

        # Find "vs", "versus", "compared to" patterns
        if "vs" in query.lower():
            parts = re.split(r'\s+vs\.?\s+|\s+versus\s+', query, flags=re.IGNORECASE)
            if len(parts) == 2:
                entities.extend([p.strip() for p in parts])

        # Default to first two capitalized words if nothing found
        if not entities:
            capitalized = [w for w in words if w[0].isupper() and len(w) > 1]
            entities = capitalized[:2]

        return entities[:5]  # Limit to 5 entities

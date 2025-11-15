# PaperPulse - AI/LLM Paper Tracking System

PaperPulse is an intelligent research paper tracking and exploration system built with advanced RAG (Retrieval-Augmented Generation) capabilities.

## Features

### 🧠 Knowledge Graph with LightRAG
- **Entity & Relationship Extraction**: Automatically extract concepts, authors, datasets, and methodologies
- **Graph-based RAG**: Use LightRAG for context-aware paper retrieval
- **Research Evolution Tracking**: Trace how research topics evolve over time
- **Community Detection**: Identify research clusters and related work

### 🔔 Notification & Recommendation
- **Personalized Recommendations**: Multi-strategy hybrid recommendation engine
- **Multi-channel Notifications**: Email, Slack, and push notifications
- **Relevance Scoring**: Intelligent paper-user matching
- **Daily/Weekly Digests**: Curated paper summaries

### 🔍 Search & QA
- **Hybrid Search**: Combines vector similarity and knowledge graph traversal
- **Question Answering**: Get answers with citations from research papers
- **Comparison Engine**: Compare papers, techniques, or approaches
- **Trend Analysis**: Analyze research trends over time

### 💬 Conversational Chatbot
- **LangGraph-powered Agent**: Intelligent conversational interface
- **Multi-tool Integration**: Seamlessly uses search, QA, comparison, and trend tools
- **Context-aware**: Maintains conversation history and user preferences

### 🚀 FastAPI Server
- **RESTful API**: Well-documented API endpoints
- **Async Operations**: High-performance async processing
- **Rate Limiting**: Built-in request throttling
- **Health Checks**: Monitoring and readiness endpoints

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Server                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Search   │  │ Recommend│  │ Chatbot  │          │
│  │ Router   │  │ Router   │  │ Router   │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼────────┐ ┌───▼──────────┐ ┌─▼──────────┐
│ Knowledge      │ │ Search & QA  │ │ Chatbot    │
│ Graph Module   │ │ Module       │ │ Module     │
│                │ │              │ │            │
│ • LightRAG    │ │ • Hybrid     │ │ • LangGraph│
│ • Entity      │ │   Search     │ │ • Tools    │
│   Extraction  │ │ • QA Engine  │ │ • Memory   │
│ • Graph Query │ │ • Comparison │ │            │
└────────────────┘ └──────────────┘ └────────────┘
```

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ (with pgvector extension)
- Redis
- OpenAI API key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AI-Paper-Tracker.git
cd AI-Paper-Tracker
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install spaCy models (optional but recommended):
```bash
python -m spacy download en_core_web_lg
# For scientific papers, if available:
python -m spacy download en_core_sci_lg
```

5. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. Initialize database:
```bash
# Run database migrations (if using Alembic)
# alembic upgrade head
```

## Usage

### Running the API Server

```bash
# Development mode with auto-reload
uvicorn src.modules.api.app:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.modules.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### Using the Modules

#### Knowledge Graph

```python
from src.modules.knowledge_graph import EntityExtractor, PaperLightRAG
from src.core.models import ProcessedDocument

# Extract entities from a paper
extractor = EntityExtractor()
entities = extractor.extract_entities(paper)

# Use LightRAG for graph-based retrieval
lightrag = PaperLightRAG(api_key="your-api-key")
lightrag.insert_paper(paper)
result = lightrag.query_related_concepts("transformer architecture")
```

#### Search & QA

```python
from src.modules.search_qa import SearchService, QAEngine

# Search papers
search_service = SearchService(api_key="your-api-key")
results = await search_service.search(
    query="attention mechanisms in transformers",
    mode="hybrid",
    top_k=10
)

# Answer questions
qa_engine = QAEngine(api_key="your-api-key")
answer = await qa_engine.answer_question(
    question="How does self-attention work?",
    relevant_chunks=chunks
)
```

#### Chatbot

```python
from src.modules.chatbot import PaperPulseChatbot

# Initialize chatbot
chatbot = PaperPulseChatbot(api_key="your-api-key")

# Chat
response = await chatbot.chat(
    query="Find recent papers on vision transformers",
    session_id="user-session-123",
    user_id="user-456"
)
```

## API Endpoints

### Search
- `POST /api/v1/search/papers` - Search papers
- `POST /api/v1/search/qa` - Ask questions
- `POST /api/v1/search/compare` - Compare entities
- `POST /api/v1/search/trends` - Analyze trends

### Recommendations
- `POST /api/v1/recommendations/profile` - Create user profile
- `GET /api/v1/recommendations/{user_id}` - Get recommendations
- `POST /api/v1/recommendations/interaction` - Log interaction

### Knowledge Graph
- `GET /api/v1/knowledge-graph/entities/{entity_id}` - Get entity
- `GET /api/v1/knowledge-graph/concepts/{concept}/related` - Related concepts
- `GET /api/v1/knowledge-graph/evolution/{topic}` - Trace evolution

### Chatbot
- `POST /api/v1/chat/message` - Send message
- `POST /api/v1/chat/session/create` - Create session
- `GET /api/v1/chat/session/{session_id}/history` - Get history

## Configuration

Key configuration options in `.env`:

- `OPENAI_API_KEY`: OpenAI API key for LLM features
- `DATABASE_URL`: PostgreSQL connection string
- `LIGHTRAG_WORKING_DIR`: Directory for LightRAG data
- `ENABLE_KNOWLEDGE_GRAPH`: Enable/disable knowledge graph features
- `ENABLE_CHATBOT`: Enable/disable chatbot features

## Development

### Project Structure

```
AI-Paper-Tracker/
├── src/
│   ├── modules/
│   │   ├── knowledge_graph/   # Knowledge graph & LightRAG
│   │   ├── notification/      # Recommendations & notifications
│   │   ├── search_qa/         # Search & QA
│   │   ├── chatbot/           # Conversational agent
│   │   └── api/               # FastAPI server
│   ├── core/
│   │   └── models.py          # Shared data models
│   └── config/
│       └── settings.py        # Configuration
├── docs/                      # Documentation
├── tests/                     # Tests
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

### Running Tests

```bash
pytest tests/ -v --cov=src
```

## Documentation

Detailed module documentation is available in the `docs/` directory:

- [System Architecture](docs/design/architecture/00-system-architecture.md)
- [Knowledge Graph Module](docs/design/modules/04-knowledge-graph.md)
- [Notification & Recommendation](docs/design/modules/05-notification-recommendation.md)
- [Search & QA Module](docs/design/modules/06-search-and-qa.md)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## Acknowledgments

- **LightRAG**: Graph-based RAG framework
- **LangGraph**: Agent workflow framework
- **FastAPI**: Modern web framework
- **OpenAI**: LLM API

## Version

Current version: 1.0.0

## Contact

For questions or support, please open an issue on GitHub.

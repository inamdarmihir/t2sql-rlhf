# Text2SQL Architecture

## System Overview

Text2SQL is a multi-agent system that converts natural language to SQL queries with semantic caching.

## Components

### 1. Frontend (Next.js + CopilotKit)
- **Port**: 3000
- **Framework**: Next.js 14 with App Router
- **UI Library**: CopilotKit for agentic interface
- **Styling**: Tailwind CSS
- **Features**:
  - Interactive chat interface
  - Real-time query execution
  - Table and JSON result views
  - Dark mode support

### 2. Backend (FastAPI + LangGraph)
- **Port**: 8000
- **Framework**: FastAPI
- **Agent System**: LangGraph hierarchical multi-agent
- **Features**:
  - REST API endpoints
  - Automatic schema detection
  - Universal database support
  - Health checks

### 3. Qdrant (Vector Database)
- **Port**: 6333
- **Purpose**: Semantic caching of SQL queries
- **Technology**: Vector similarity search
- **Threshold**: 0.85 (configurable)

### 4. Database (SQLite/PostgreSQL/MySQL)
- **Default**: SQLite with sample shopping data
- **Support**: Any SQLAlchemy-compatible database
- **Schema**: Auto-detected dynamically

## Multi-Agent Workflow

```
┌─────────────────────────────────────────────────────┐
│                   User Question                      │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │    Cache Agent        │
         │  (Check Qdrant)       │
         └───────────┬───────────┘
                     │
            ┌────────┴────────┐
            │                 │
         Cache Hit         Cache Miss
            │                 │
            │                 ▼
            │     ┌───────────────────────┐
            │     │   SQL Generator       │
            │     │   (GPT-4)             │
            │     └───────────┬───────────┘
            │                 │
            └────────┬────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │    Executor Agent     │
         │  (Run Query + Cache)  │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │       Results         │
         └───────────────────────┘
```

## Agent Details

### Cache Agent
- **Purpose**: Check for semantically similar queries
- **Technology**: Qdrant vector search with embeddings
- **Decision**: Route to Executor (hit) or SQL Generator (miss)
- **Performance**: Sub-second retrieval

### SQL Generator Agent
- **Purpose**: Generate SQL from natural language
- **Technology**: GPT-4 with schema context
- **Input**: Question + Database schema
- **Output**: Valid SQL query

### Executor Agent
- **Purpose**: Execute SQL and manage cache
- **Actions**:
  1. Execute SQL query
  2. Return results
  3. Store in Qdrant (if new)
- **Error Handling**: Graceful error messages

## Data Flow

### Query Execution
1. User submits question via UI
2. Frontend sends POST to `/api/query`
3. Backend initializes agent state
4. Cache Agent checks Qdrant
5. If miss, SQL Generator creates query
6. Executor runs query and caches
7. Results returned to frontend
8. UI displays SQL + results

### Caching Mechanism
1. Question → OpenAI Embeddings (1536 dimensions)
2. Vector stored in Qdrant with SQL payload
3. Future queries → Cosine similarity search
4. If similarity > 0.85 → Cache hit
5. Return cached SQL instantly

## API Endpoints

### POST /api/query
```json
Request:
{
  "question": "Show me all customers"
}

Response:
{
  "sql_query": "SELECT * FROM customers",
  "results": [...],
  "cached": false,
  "error": null,
  "message_count": 3
}
```

### GET /api/schema
```json
Response:
{
  "schema": "Table: customers\nColumns: id (INTEGER), ..."
}
```

### GET /health
```json
Response:
{
  "status": "healthy"
}
```

## Technology Stack

### Backend
- Python 3.12
- FastAPI (async web framework)
- LangGraph (agent orchestration)
- LangChain (LLM integration)
- SQLAlchemy (database ORM)
- Qdrant Client (vector DB)
- OpenAI API (embeddings + chat)

### Frontend
- Node.js 20
- Next.js 14 (React framework)
- CopilotKit (agentic UI)
- TypeScript
- Tailwind CSS
- Axios (HTTP client)

### Infrastructure
- Docker & Docker Compose
- Qdrant (vector database)
- SQLite/PostgreSQL/MySQL

## Deployment

### Development
```bash
start-dev.bat  # Windows
# or
docker-compose up -d
```

### Production
```bash
docker-compose up -d --build
```

### Scaling
- Backend: Horizontal scaling via Docker Compose
- Qdrant: Cluster mode for high availability
- Database: Connection pooling + read replicas

## Security Considerations

1. **API Keys**: Stored in .env (not committed)
2. **CORS**: Configured in FastAPI
3. **SQL Injection**: Parameterized queries via SQLAlchemy
4. **Rate Limiting**: Recommended for production
5. **Authentication**: Add JWT/OAuth for production

## Performance

### Metrics
- **Cache Hit**: < 100ms
- **Cache Miss**: 2-5 seconds (GPT-4 generation)
- **Query Execution**: Depends on database
- **Embedding Generation**: ~500ms

### Optimization
- Qdrant indexing for fast retrieval
- Connection pooling for database
- Async operations throughout
- Lazy initialization of resources

## Monitoring

### Health Checks
- Backend: `/health` endpoint
- Qdrant: Built-in health endpoint
- Docker: Health check configurations

### Logging
- FastAPI access logs
- Agent execution traces
- Error tracking

## Future Enhancements

1. **Query Validation**: Pre-execution SQL validation
2. **Result Caching**: Cache query results too
3. **Multi-Database**: Support multiple databases
4. **Query History**: Store user query history
5. **Analytics**: Track cache hit rates
6. **Fine-tuning**: Custom SQL generation model
7. **Streaming**: Stream results for large datasets
8. **Visualization**: Auto-generate charts

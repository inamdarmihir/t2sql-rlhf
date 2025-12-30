# Text2SQL Multi-Agent System with Qdrant Cache

AI-powered natural language to SQL converter with semantic caching and agentic UI.

## 🚀 Quick Start

```bash
# 1. Set your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 2. Start all services
docker-compose up -d

# 3. Open http://localhost:3000
```

## ✨ Features

- **🤖 Agentic UI with CopilotKit**: Interactive AI chat interface
- **🔄 Hierarchical Multi-Agent System**: Cache → SQL Generator → Executor
- **⚡ Semantic Caching**: Lightning-fast query retrieval with Qdrant
- **🗄️ Universal Database Support**: Works with any SQLAlchemy-supported database
- **🎯 Automatic Schema Detection**: Reads your database structure dynamically
- **🐳 Docker Compose Stack**: One command to run everything
- **👍👎 RL Feedback Loop**: Human feedback improves SQL generation over time
  - **2+ thumbs down**: Warning - query type needs review
  - **3+ thumbs down**: Critical - agent needs retraining
  - **2+ thumbs up**: Good performance
  - **3+ thumbs up**: Excellent - consistently performing well

## 📦 Services

- **Frontend** (Port 3000): Next.js + CopilotKit UI
- **Backend** (Port 8000): FastAPI + LangGraph
- **Qdrant** (Port 6333): Vector database for caching

## 🎯 Usage

### Web Interface

1. Open http://localhost:3000
2. Type a natural language question
3. View generated SQL and results
4. **Provide feedback**: Click thumbs up/down to train the AI
   - Thumbs up: Query is correct
   - Thumbs down: Query is incorrect
5. Watch the agent improve over time!

**Example Questions:**
```
Show me all customers from California
What are the top 5 best-selling products?
What is the total revenue by category?
Which customers spent more than $500?
```

### RL Feedback System

The agent learns from your feedback:

- **First query**: No feedback data, generates SQL normally
- **After 2 thumbs down**: ⚠️ Warning shown, agent becomes more careful
- **After 3 thumbs down**: 🚨 Critical alert, agent needs retraining
- **After 2 thumbs up**: ✅ Good performance indicator
- **After 3 thumbs up**: 🌟 Excellent performance, agent continues approach

The system uses similar successful queries as examples for future generations.

### API

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me all customers"}'
```

## 🗄️ Using Your Own Database

Update `backend/.env`:

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# MySQL
DATABASE_URL=mysql://user:password@localhost:3306/mydb

# SQLite (default)
DATABASE_URL=sqlite:///./test.db
```

The system automatically detects your schema!

## 🛠️ Development

### Quick Start (Development Mode)
```bash
start-dev.bat
```

This will start:
- Qdrant (if not running)
- Backend on port 8000
- Frontend on port 3000

### Manual Start

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
.
├── backend/
│   ├── main.py              # Text2SQL implementation
│   ├── api.py               # FastAPI REST API
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js app
│   ├── components/          # React components
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml       # Docker orchestration
├── setup.bat                # Windows setup script
└── README.md
```

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild
docker-compose up -d --build

# Clean slate
docker-compose down -v
```

## 🔧 Configuration

### Cache Similarity Threshold
Edit `backend/main.py`, `QdrantCache.search()` method (default: 0.85)

### OpenAI Model
Edit agent nodes in `backend/main.py` (default: gpt-4)

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │ :3000 (Next.js + CopilotKit)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Backend   │ :8000 (FastAPI + LangGraph)
└──────┬──────┘
       │
       ├──────────┐
       ▼          ▼
┌──────────┐  ┌────────┐
│  Qdrant  │  │   DB   │
│  :6333   │  │ SQLite │
└──────────┘  └────────┘
```

### Multi-Agent Workflow

```
User Question → Cache Agent → [Cache Hit?]
                              ├─ Yes → Executor → Results
                              └─ No → SQL Generator → Executor → Results
```

## 🔍 Sample Database

Includes a shopping/sales database with:
- **customers**: Customer information
- **products**: Product catalog
- **sales**: Transaction records
- **sales_summary**: Daily metrics

## 📊 API Endpoints

- `POST /api/query` - Execute natural language query
- `POST /api/feedback` - Submit thumbs up/down feedback
- `GET /api/feedback/stats` - Get overall feedback statistics
- `GET /api/schema` - Get database schema
- `GET /health` - Health check
- `GET /docs` - API documentation

## 🚨 Troubleshooting

### Services won't start
```bash
docker info  # Check Docker is running
docker-compose logs -f  # View logs
```

### Port conflicts
Edit `docker-compose.yml` ports section

### API key error
Verify `.env` has valid `OPENAI_API_KEY`

## 📝 Requirements

- Docker Desktop
- OpenAI API key
- 4GB RAM minimum

## 📄 License

MIT

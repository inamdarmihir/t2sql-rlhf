from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from main import Text2SQLGraph

app = FastAPI(title="Text2SQL API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Text2SQL graph
text2sql = None

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql_query: str
    results: List[Dict[str, Any]]
    cached: bool
    error: Optional[str] = None
    message_count: int
    feedback_metrics: Optional[Dict] = None
    similar_examples: Optional[List[Dict]] = None

class FeedbackRequest(BaseModel):
    question: str
    sql_query: str
    feedback: str  # 'up' or 'down'

class FeedbackResponse(BaseModel):
    success: bool
    metrics: Dict
    message: str

@app.on_event("startup")
async def startup_event():
    global text2sql
    text2sql = Text2SQLGraph()
    print("✓ Text2SQL system initialized")

@app.get("/")
async def root():
    return {
        "message": "Text2SQL API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/api/query",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/query", response_model=QueryResponse)
async def query_database(request: QueryRequest):
    """
    Query the database using natural language with RL feedback
    """
    try:
        if not text2sql:
            raise HTTPException(status_code=503, detail="Text2SQL system not initialized")
        
        result = text2sql.query(request.question)
        
        return QueryResponse(
            sql_query=result.get("sql_query", ""),
            results=result.get("results", []),
            cached=result.get("cached", False),
            error=result.get("error"),
            message_count=len(result.get("messages", [])),
            feedback_metrics=result.get("feedback_metrics"),
            similar_examples=result.get("similar_examples")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit human feedback for RL training
    """
    try:
        if not text2sql:
            raise HTTPException(status_code=503, detail="Text2SQL system not initialized")
        
        if request.feedback not in ['up', 'down']:
            raise HTTPException(status_code=400, detail="Feedback must be 'up' or 'down'")
        
        metrics = text2sql.add_feedback(
            request.question,
            request.sql_query,
            request.feedback
        )
        
        message = "Feedback recorded successfully"
        if metrics.get('warning'):
            message = metrics['warning']
        
        return FeedbackResponse(
            success=True,
            metrics=metrics,
            message=message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback/stats")
async def get_feedback_stats():
    """
    Get overall feedback statistics
    """
    try:
        if not text2sql:
            raise HTTPException(status_code=503, detail="Text2SQL system not initialized")
        
        stats = text2sql.get_feedback_stats()
        failed_patterns = text2sql.get_failed_patterns()
        
        return {
            "overall": stats,
            "failed_patterns": failed_patterns
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schema")
async def get_schema():
    """
    Get the database schema
    """
    try:
        if not text2sql:
            raise HTTPException(status_code=503, detail="Text2SQL system not initialized")
        
        schema = text2sql.db_manager.get_schema()
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

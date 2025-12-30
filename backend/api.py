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
    Query the database using natural language
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
            message_count=len(result.get("messages", []))
        )
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

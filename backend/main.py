import os
import json
import hashlib
import functools
import operator
import asyncio
from typing import TypedDict, Optional, Dict, List, Any, Annotated, Sequence
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from feedback_store import FeedbackStore

# Load environment variables
load_dotenv(override=True)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
COLLECTION_NAME = "sql_query_cache"

# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    question: str
    sql_query: str
    results: list
    cached: bool
    error: str
    schema: str
    next: str
    feedback_metrics: dict
    similar_examples: list

# ============================================================================
# Database Manager
# ============================================================================

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
    
    def get_schema(self) -> str:
        """Get database schema information"""
        inspector = inspect(self.engine)
        schema_info = []
        
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            col_info = [f"{col['name']} ({col['type']})" for col in columns]
            schema_info.append(f"Table: {table_name}\nColumns: {', '.join(col_info)}")
        
        return "\n\n".join(schema_info)
    
    def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql_query))
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

# ============================================================================
# Qdrant Cache (Lazy Initialization)
# ============================================================================

class QdrantCache:
    def __init__(self):
        self.client = None
        self.embeddings = None
        self.collection_name = COLLECTION_NAME
        self._initialized = False
    
    def _lazy_init(self):
        """Lazy initialization of Qdrant client"""
        if not self._initialized:
            self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
            self.embeddings = OpenAIEmbeddings()
            self._ensure_collection()
            self._initialized = True
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
    
    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def search(self, question: str, threshold: float = 0.85) -> Optional[Dict]:
        """Search for cached SQL query"""
        self._lazy_init()
        vector = self.embeddings.embed_query(question)
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=1
        )
        
        if results and results[0].score >= threshold:
            return {
                "sql_query": results[0].payload["sql_query"],
                "score": results[0].score,
                "original_question": results[0].payload["question"]
            }
        return None
    
    def store(self, question: str, sql_query: str):
        """Store question-SQL pair in cache"""
        self._lazy_init()
        vector = self.embeddings.embed_query(question)
        point_id = self._generate_id(question)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"question": question, "sql_query": sql_query}
                )
            ]
        )

# ============================================================================
# Agent Tools
# ============================================================================

def create_cache_checker(cache):
    """Create cache checking tool"""
    def check_cache(question: str) -> str:
        """Check if a similar SQL query exists in cache"""
        cached_result = cache.search(question)
        if cached_result:
            print(f"✓ Cache hit! (score: {cached_result['score']:.2f})")
            return f"CACHED_QUERY: {cached_result['sql_query']}"
        else:
            print("✗ Cache miss - need to generate new query")
            return "NO_CACHE"
    return check_cache

def create_sql_generator(db_manager):
    """Create SQL generation tool"""
    def generate_sql(question: str) -> str:
        """Generate SQL query from natural language question"""
        schema = db_manager.get_schema()
        prompt = f"""Generate a SQL query for this question: {question}

Database Schema:
{schema}

Return ONLY the SQL query, no explanations."""
        
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        response = llm.invoke(prompt)
        sql_query = response.content.strip()
        
        # Remove markdown code blocks if present
        if sql_query.startswith("```"):
            sql_query = sql_query.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        
        print(f"Generated SQL: {sql_query}")
        return sql_query
    return generate_sql

def create_sql_executor(db_manager, cache):
    """Create SQL execution tool"""
    def execute_sql(sql_query: str, question: str = "") -> str:
        """Execute SQL query and return results"""
        try:
            results = db_manager.execute_query(sql_query)
            
            # Cache the query if question is provided
            if question:
                cache.store(question, sql_query)
                print("✓ Query cached for future use")
            
            return json.dumps(results, indent=2)
        except Exception as e:
            error_msg = f"Error executing query: {str(e)}"
            print(f"✗ {error_msg}")
            return error_msg
    return execute_sql

# ============================================================================
# Agent Nodes
# ============================================================================

def create_supervisor_node(llm: ChatOpenAI, members: List[str]):
    """Create supervisor agent that routes to team members"""
    system_prompt = f"""You are a supervisor managing a Text2SQL team with these workers: {members}.
    
Your job is to coordinate the team to answer user questions about the database:
1. First, ask cache_agent to check if we have a cached query
2. If no cache, ask sql_generator to create the SQL query
3. Finally, ask executor to run the query and return results

Respond with the worker name to route to next, or FINISH when done."""

    options = ["FINISH"] + members
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", f"Given the conversation, who should act next? Options: {options}")
    ])
    
    def supervisor_node(state: AgentState) -> AgentState:
        result = (prompt | llm).invoke(state)
        next_agent = result.content.strip()
        
        # Parse the response to get the next agent
        for option in options:
            if option.lower() in next_agent.lower():
                state["next"] = option
                break
        else:
            state["next"] = "FINISH"
        
        return state
    
    return supervisor_node

def cache_agent_node(cache):
    """Cache checking agent node"""
    def node(state: AgentState) -> AgentState:
        question = state["question"]
        cached_result = cache.search(question)
        
        if cached_result:
            state["sql_query"] = cached_result["sql_query"]
            state["cached"] = True
            msg = f"✓ Cache hit! Found cached query: {cached_result['sql_query']}"
            print(msg)
            state["messages"].append(AIMessage(content=msg, name="cache_agent"))
            state["next"] = "executor"
        else:
            state["cached"] = False
            msg = "✗ Cache miss - routing to SQL generator"
            print(msg)
            state["messages"].append(AIMessage(content=msg, name="cache_agent"))
            state["next"] = "sql_generator"
        
        return state
    return node

def sql_generator_node(db_manager, feedback_store):
    """SQL generation agent node with RL feedback"""
    def node(state: AgentState) -> AgentState:
        if state.get("cached"):
            state["next"] = "executor"
            return state
        
        schema = db_manager.get_schema()
        question = state["question"]
        
        # Get feedback metrics for this query type
        metrics = feedback_store.get_query_metrics(question)
        state["feedback_metrics"] = metrics
        
        # Get similar successful queries for learning
        similar_examples = feedback_store.get_similar_successful_queries(question)
        state["similar_examples"] = similar_examples
        
        # Build enhanced prompt with RL feedback
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        
        # Add performance context to prompt
        performance_context = ""
        if metrics['performance_level'] == 'critical':
            performance_context = f"""
⚠️ CRITICAL WARNING: Similar queries have failed {metrics['thumbs_down']} times.
Previous attempts were incorrect. Be extra careful with this query type.
"""
        elif metrics['performance_level'] == 'poor':
            performance_context = f"""
⚠️ WARNING: Similar queries have {metrics['thumbs_down']} failures.
Review the query carefully before generating.
"""
        elif metrics['performance_level'] == 'excellent':
            performance_context = f"""
✅ This query type has {metrics['thumbs_up']} successes. Continue with similar approach.
"""
        
        # Add successful examples if available
        examples_context = ""
        if similar_examples:
            examples_context = "\n\nSuccessful similar queries for reference:"
            for i, ex in enumerate(similar_examples, 1):
                examples_context += f"\nExample {i}:"
                examples_context += f"\n  Question: {ex['question']}"
                examples_context += f"\n  SQL: {ex['sql_query']}"
        
        prompt = f"""Generate a SQL query for: {question}

Database Schema:
{schema}
{performance_context}
{examples_context}

Return ONLY the SQL query, no explanations."""
        
        response = llm.invoke(prompt)
        sql_query = response.content.strip()
        
        # Clean up markdown
        if sql_query.startswith("```"):
            sql_query = sql_query.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        
        state["sql_query"] = sql_query
        
        # Add performance warning to message
        msg = f"Generated SQL: {sql_query}"
        if metrics.get('warning'):
            msg += f"\n{metrics['warning']}"
        
        print(msg)
        state["messages"].append(AIMessage(content=msg, name="sql_generator"))
        state["next"] = "executor"
        
        return state
    return node

def executor_node(db_manager, cache):
    """SQL execution agent node"""
    def node(state: AgentState) -> AgentState:
        sql_query = state["sql_query"]
        question = state["question"]
        
        try:
            results = db_manager.execute_query(sql_query)
            state["results"] = results
            
            # Cache if not already cached
            if not state.get("cached"):
                cache.store(question, sql_query)
                print("✓ Query cached for future use")
            
            msg = f"Executed query successfully. Found {len(results)} rows."
            print(msg)
            state["messages"].append(AIMessage(content=msg, name="executor"))
            state["next"] = "FINISH"
            
        except Exception as e:
            state["error"] = str(e)
            msg = f"✗ Error executing query: {e}"
            print(msg)
            state["messages"].append(AIMessage(content=msg, name="executor"))
            state["next"] = "FINISH"
        
        return state
    return node

# ============================================================================
# Hierarchical Multi-Agent Workflow
# ============================================================================

class Text2SQLGraph:
    def __init__(self):
        self.cache = QdrantCache()
        self.db_manager = DatabaseManager()
        self.feedback_store = FeedbackStore()
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        
        # Build hierarchical graph
        self.graph = self._build_hierarchical_graph()
    
    def _build_hierarchical_graph(self):
        """Build hierarchical agent team graph"""
        workflow = StateGraph(AgentState)
        
        # Create agent nodes
        members = ["cache_agent", "sql_generator", "executor"]
        
        # Add nodes
        workflow.add_node("cache_agent", cache_agent_node(self.cache))
        workflow.add_node("sql_generator", sql_generator_node(self.db_manager, self.feedback_store))
        workflow.add_node("executor", executor_node(self.db_manager, self.cache))
        
        # Define conditional routing based on agent decisions
        def route_after_cache(state: AgentState) -> str:
            if state.get("cached"):
                return "executor"
            return "sql_generator"
        
        def route_after_generator(state: AgentState) -> str:
            return "executor"
        
        def route_after_executor(state: AgentState) -> str:
            return END
        
        # Set up workflow
        workflow.set_entry_point("cache_agent")
        workflow.add_conditional_edges(
            "cache_agent",
            route_after_cache,
            {"executor": "executor", "sql_generator": "sql_generator"}
        )
        workflow.add_edge("sql_generator", "executor")
        workflow.add_edge("executor", END)
        
        return workflow.compile()
    
    def query(self, question: str) -> dict:
        """Process a natural language question"""
        schema = self.db_manager.get_schema()
        
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "sql_query": "",
            "results": [],
            "cached": False,
            "error": "",
            "schema": schema,
            "next": "",
            "feedback_metrics": {},
            "similar_examples": []
        }
        
        final_state = self.graph.invoke(initial_state)
        return final_state
    
    def add_feedback(self, question: str, sql_query: str, feedback: str) -> Dict:
        """Add human feedback for RL training"""
        return self.feedback_store.add_feedback(question, sql_query, feedback)
    
    def get_feedback_stats(self) -> Dict:
        """Get overall feedback statistics"""
        return self.feedback_store.get_overall_stats()
    
    def get_failed_patterns(self) -> List[Dict]:
        """Get query patterns that need improvement"""
        return self.feedback_store.get_failed_patterns()

# ============================================================================
# Setup & Main
# ============================================================================

def setup_sample_database():
    """Create sample shopping/sales database with test data"""
    db = DatabaseManager()
    
    with db.engine.connect() as conn:
        # Create tables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                city TEXT,
                state TEXT,
                registration_date TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                stock_quantity INTEGER,
                supplier TEXT
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                sale_date TEXT NOT NULL,
                payment_method TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sales_summary (
                summary_id INTEGER PRIMARY KEY,
                sale_date TEXT NOT NULL,
                total_sales REAL,
                total_orders INTEGER,
                average_order_value REAL
            )
        """))
        
        # Insert sample customers
        conn.execute(text("""
            INSERT OR IGNORE INTO customers (customer_id, first_name, last_name, email, phone, city, state, registration_date) VALUES
            (1, 'John', 'Smith', 'john.smith@email.com', '555-0101', 'New York', 'NY', '2024-01-10'),
            (2, 'Emma', 'Johnson', 'emma.j@email.com', '555-0102', 'Los Angeles', 'CA', '2024-01-15'),
            (3, 'Michael', 'Brown', 'mbrown@email.com', '555-0103', 'Chicago', 'IL', '2024-01-20'),
            (4, 'Sarah', 'Davis', 'sarah.d@email.com', '555-0104', 'Houston', 'TX', '2024-02-01'),
            (5, 'James', 'Wilson', 'jwilson@email.com', '555-0105', 'Phoenix', 'AZ', '2024-02-05')
        """))
        
        # Insert sample products
        conn.execute(text("""
            INSERT OR IGNORE INTO products (product_id, product_name, category, price, stock_quantity, supplier) VALUES
            (1, 'Laptop Pro 15', 'Electronics', 1299.99, 50, 'TechCorp'),
            (2, 'Wireless Mouse', 'Electronics', 29.99, 200, 'TechCorp'),
            (3, 'Mechanical Keyboard', 'Electronics', 89.99, 150, 'TechCorp'),
            (4, 'USB-C Hub', 'Electronics', 49.99, 100, 'AccessoriesInc'),
            (5, 'Monitor 27inch', 'Electronics', 349.99, 75, 'DisplayTech'),
            (6, 'Desk Chair', 'Furniture', 199.99, 30, 'OfficeFurn'),
            (7, 'Standing Desk', 'Furniture', 499.99, 20, 'OfficeFurn'),
            (8, 'Desk Lamp', 'Furniture', 39.99, 80, 'LightingCo'),
            (9, 'Notebook Set', 'Stationery', 12.99, 300, 'PaperPlus'),
            (10, 'Pen Pack', 'Stationery', 8.99, 500, 'PaperPlus')
        """))
        
        # Insert sample sales
        conn.execute(text("""
            INSERT OR IGNORE INTO sales (sale_id, customer_id, product_id, quantity, total_amount, sale_date, payment_method) VALUES
            (1, 1, 1, 1, 1299.99, '2024-02-15', 'Credit Card'),
            (2, 1, 2, 2, 59.98, '2024-02-15', 'Credit Card'),
            (3, 2, 3, 1, 89.99, '2024-02-16', 'PayPal'),
            (4, 2, 4, 1, 49.99, '2024-02-16', 'PayPal'),
            (5, 3, 5, 1, 349.99, '2024-02-17', 'Credit Card'),
            (6, 3, 6, 1, 199.99, '2024-02-17', 'Credit Card'),
            (7, 4, 7, 1, 499.99, '2024-02-18', 'Debit Card'),
            (8, 4, 8, 2, 79.98, '2024-02-18', 'Debit Card'),
            (9, 5, 9, 5, 64.95, '2024-02-19', 'Cash'),
            (10, 5, 10, 3, 26.97, '2024-02-19', 'Cash'),
            (11, 1, 3, 1, 89.99, '2024-02-20', 'Credit Card'),
            (12, 2, 1, 1, 1299.99, '2024-02-21', 'Credit Card'),
            (13, 3, 2, 3, 89.97, '2024-02-22', 'PayPal'),
            (14, 4, 9, 10, 129.90, '2024-02-23', 'Debit Card'),
            (15, 5, 5, 1, 349.99, '2024-02-24', 'Credit Card')
        """))
        
        # Insert sales summary
        conn.execute(text("""
            INSERT OR IGNORE INTO sales_summary (summary_id, sale_date, total_sales, total_orders, average_order_value) VALUES
            (1, '2024-02-15', 1359.97, 2, 679.99),
            (2, '2024-02-16', 139.98, 2, 69.99),
            (3, '2024-02-17', 549.98, 2, 274.99),
            (4, '2024-02-18', 579.97, 2, 289.99),
            (5, '2024-02-19', 91.92, 2, 45.96)
        """))
        
        conn.commit()
    
    print("✓ Shopping/Sales database created successfully\n")

def main():
    print("=== Text2SQL Multi-Agent System with Qdrant Cache ===\n")
    
    # Setup sample database
    setup_sample_database()
    
    # Initialize the graph
    text2sql = Text2SQLGraph()
    
    # Example queries for shopping/sales database
    questions = [
        "Show me all customers from California",
        "What are the top 5 best-selling products?",
        "Show me all customers from California",  # This should hit the cache
        "What is the total revenue by category?",
        "Find all sales made with credit card",
        "Which customers spent more than $500?",
        "Show me products that are low in stock (less than 50 units)"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {question}")
        print('='*60)
        
        result = text2sql.query(question)
        
        if result["error"]:
            print(f"\n❌ Error: {result['error']}")
        else:
            print(f"\nSQL Query: {result['sql_query']}")
            print(f"\nResults ({len(result['results'])} rows):")
            print(json.dumps(result['results'], indent=2))

if __name__ == "__main__":
    main()

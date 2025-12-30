# Reinforcement Learning Feedback Loop

## Overview

The Text2SQL system now includes a human-in-the-loop reinforcement learning feedback mechanism that improves SQL generation over time based on thumbs up/down feedback.

## How It Works

### 1. Feedback Collection

Users can provide feedback on generated SQL queries:
- **Thumbs Up (👍)**: Query is correct
- **Thumbs Down (👎)**: Query is incorrect

### 2. Performance Tracking

The system tracks cumulative feedback for each query pattern:

```python
{
  "thumbs_up": 3,
  "thumbs_down": 1,
  "total_feedback": 4,
  "success_rate": 75.0,
  "performance_level": "good"
}
```

### 3. Performance Levels

Based on feedback count, queries are classified:

| Level | Criteria | Agent Behavior |
|-------|----------|----------------|
| **Critical** | 3+ thumbs down | 🚨 Shows critical warning, agent becomes extra careful |
| **Poor** | 2+ thumbs down | ⚠️ Shows warning, agent reviews carefully |
| **Excellent** | 3+ thumbs up | ✅ Shows success, agent continues approach |
| **Good** | 2+ thumbs up | ✅ Shows good performance |
| **Neutral** | Mixed or minimal feedback | No special handling |

### 4. Agent Adaptation

The SQL Generator agent adapts based on feedback:

#### Critical Performance (3+ thumbs down)
```
⚠️ CRITICAL WARNING: Similar queries have failed 3 times.
Previous attempts were incorrect. Be extra careful with this query type.
```

The agent receives this context in its prompt, making it more cautious.

#### Excellent Performance (3+ thumbs up)
```
✅ This query type has 3 successes. Continue with similar approach.
```

The agent is encouraged to maintain its strategy.

### 5. Learning from Success

The system provides successful examples to the agent:

```python
similar_examples = [
  {
    "question": "Show me all customers from California",
    "sql_query": "SELECT * FROM customers WHERE state = 'CA'"
  },
  {
    "question": "List California customers",
    "sql_query": "SELECT * FROM customers WHERE state = 'California'"
  }
]
```

These examples are included in the prompt for similar future queries.

## Implementation Details

### Backend Components

#### 1. FeedbackStore (`backend/feedback_store.py`)

Manages feedback data and metrics:

```python
class FeedbackStore:
    def add_feedback(question, sql_query, feedback) -> Dict
    def get_query_metrics(question) -> Dict
    def get_similar_successful_queries(question) -> List[Dict]
    def get_failed_patterns() -> List[Dict]
    def get_overall_stats() -> Dict
```

#### 2. Enhanced SQL Generator

The SQL generator now:
1. Retrieves feedback metrics for the query type
2. Gets similar successful examples
3. Builds enhanced prompt with performance context
4. Generates SQL with learned knowledge

```python
def sql_generator_node(db_manager, feedback_store):
    # Get feedback metrics
    metrics = feedback_store.get_query_metrics(question)
    
    # Get successful examples
    similar_examples = feedback_store.get_similar_successful_queries(question)
    
    # Build enhanced prompt
    prompt = f"""
    {performance_context}
    {examples_context}
    Generate SQL for: {question}
    """
```

#### 3. API Endpoints

**POST /api/feedback**
```json
Request:
{
  "question": "Show me all customers",
  "sql_query": "SELECT * FROM customers",
  "feedback": "up"
}

Response:
{
  "success": true,
  "metrics": {
    "thumbs_up": 1,
    "thumbs_down": 0,
    "total_feedback": 1,
    "performance_level": "neutral",
    "success_rate": 100.0
  },
  "message": "Feedback recorded successfully"
}
```

**GET /api/feedback/stats**
```json
Response:
{
  "overall": {
    "total_feedback": 15,
    "thumbs_up": 12,
    "thumbs_down": 3,
    "success_rate": 80.0,
    "unique_queries": 8,
    "critical_queries": 1,
    "excellent_queries": 2
  },
  "failed_patterns": [
    {
      "question_pattern": "complex join query",
      "thumbs_down": 3,
      "thumbs_up": 0,
      "total": 3
    }
  ]
}
```

### Frontend Components

#### 1. Feedback Buttons

Thumbs up/down buttons appear next to generated SQL:

```tsx
<button onClick={() => handleFeedback('up')}>
  <ThumbsUp />
</button>
<button onClick={() => handleFeedback('down')}>
  <ThumbsDown />
</button>
```

#### 2. Performance Badges

Visual indicators show query performance:

- 🚨 **Critical - Needs Review** (red)
- ⚠️ **Poor Performance** (orange)
- ✅ **Good Performance** (blue)
- 🌟 **Excellent Performance** (green)

#### 3. Metrics Display

Shows cumulative feedback statistics:

```
Thumbs Up: 3
Thumbs Down: 1
Total Feedback: 4
Success Rate: 75%
```

#### 4. Similar Examples

Displays successful similar queries for learning:

```
Similar Successful Queries (2)
1. Show me all customers from CA
   SELECT * FROM customers WHERE state = 'CA'
2. List California customers
   SELECT * FROM customers WHERE state = 'California'
```

## Data Storage

Feedback is stored in `feedback_data.json`:

```json
[
  {
    "question": "Show me all customers",
    "sql_query": "SELECT * FROM customers",
    "feedback": "up",
    "timestamp": "2025-12-30T15:30:00"
  },
  {
    "question": "Show me all customers",
    "sql_query": "SELECT * FROM customers",
    "feedback": "up",
    "timestamp": "2025-12-30T15:35:00"
  }
]
```

## Benefits

### 1. Continuous Improvement
- Agent learns from mistakes
- Successful patterns are reinforced
- Failed patterns trigger warnings

### 2. Transparency
- Users see performance metrics
- Clear indicators of query reliability
- Feedback impact is visible

### 3. Human-in-the-Loop
- Humans provide ground truth
- No need for labeled training data
- Real-world validation

### 4. Adaptive Behavior
- Agent adjusts based on feedback
- More careful with problematic queries
- Confident with successful patterns

## Future Enhancements

### 1. Advanced RL Algorithms
- Implement Q-learning or policy gradient
- Use feedback as reward signal
- Fine-tune model weights

### 2. Pattern Recognition
- Identify common failure patterns
- Cluster similar queries
- Automatic error categorization

### 3. Active Learning
- Request feedback on uncertain queries
- Prioritize learning from edge cases
- Suggest corrections

### 4. Multi-User Feedback
- Aggregate feedback across users
- Weight by user expertise
- Consensus-based metrics

### 5. Automated Testing
- Generate test cases from feedback
- Regression testing for failed patterns
- Continuous validation

## Usage Example

### Step 1: Initial Query
```
User: "Show me all customers from California"
Agent: SELECT * FROM customers WHERE state = 'California'
```

### Step 2: Provide Feedback
```
User clicks: 👎 (Thumbs Down)
System: Feedback recorded (1 down, 0 up)
```

### Step 3: Second Attempt
```
User: "Show me all customers from California"
Agent receives warning: "⚠️ WARNING: Similar queries have 1 failure"
Agent: SELECT * FROM customers WHERE state = 'CA'
```

### Step 4: Positive Feedback
```
User clicks: 👍 (Thumbs Up)
System: Feedback recorded (1 down, 1 up)
```

### Step 5: Learning Applied
```
User: "List customers from California"
Agent sees similar successful query as example
Agent: SELECT * FROM customers WHERE state = 'CA'
```

## Monitoring

Track system performance:

```bash
curl http://localhost:8000/api/feedback/stats
```

View:
- Overall success rate
- Critical query patterns
- Excellent query patterns
- Total feedback count

## Best Practices

1. **Provide Consistent Feedback**: Help the system learn patterns
2. **Review Critical Queries**: Address queries with 3+ thumbs down
3. **Monitor Success Rate**: Track overall system improvement
4. **Use Similar Examples**: Learn from successful patterns
5. **Regular Review**: Check failed patterns periodically

## Conclusion

The RL feedback loop transforms Text2SQL from a static system into a continuously improving AI that learns from human expertise. Each piece of feedback makes the system smarter and more reliable.

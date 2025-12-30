import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

class FeedbackStore:
    """Store and manage human feedback for RL training"""
    
    def __init__(self, feedback_file: str = "feedback_data.json"):
        self.feedback_file = feedback_file
        self.feedback_data = self._load_feedback()
        self.query_scores = defaultdict(lambda: {"up": 0, "down": 0, "total": 0})
        self._calculate_scores()
    
    def _load_feedback(self) -> List[Dict]:
        """Load feedback from JSON file"""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_feedback(self):
        """Save feedback to JSON file"""
        with open(self.feedback_file, 'w') as f:
            json.dump(self.feedback_data, f, indent=2)
    
    def _calculate_scores(self):
        """Calculate cumulative scores for each question pattern"""
        for entry in self.feedback_data:
            question = entry['question'].lower()
            feedback = entry['feedback']
            
            self.query_scores[question]['total'] += 1
            if feedback == 'up':
                self.query_scores[question]['up'] += 1
            else:
                self.query_scores[question]['down'] += 1
    
    def add_feedback(self, question: str, sql_query: str, feedback: str) -> Dict:
        """
        Add human feedback for a query
        
        Args:
            question: Natural language question
            sql_query: Generated SQL query
            feedback: 'up' or 'down'
        
        Returns:
            Performance metrics and warnings
        """
        entry = {
            "question": question,
            "sql_query": sql_query,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
        
        self.feedback_data.append(entry)
        self._save_feedback()
        
        # Update scores
        question_lower = question.lower()
        self.query_scores[question_lower]['total'] += 1
        if feedback == 'up':
            self.query_scores[question_lower]['up'] += 1
        else:
            self.query_scores[question_lower]['down'] += 1
        
        # Calculate metrics
        return self.get_query_metrics(question)
    
    def get_query_metrics(self, question: str) -> Dict:
        """Get performance metrics for a question"""
        question_lower = question.lower()
        scores = self.query_scores[question_lower]
        
        up_count = scores['up']
        down_count = scores['down']
        total = scores['total']
        
        # Calculate performance level
        performance_level = "unknown"
        warning = None
        
        if down_count >= 3:
            performance_level = "critical"
            warning = "⚠️ CRITICAL: This query type is consistently wrong. Agent needs retraining."
        elif down_count >= 2:
            performance_level = "poor"
            warning = "⚠️ WARNING: This query type has multiple failures. Review needed."
        elif up_count >= 3:
            performance_level = "excellent"
            warning = "✅ EXCELLENT: This query type is consistently performing well."
        elif up_count >= 2:
            performance_level = "good"
            warning = "✅ GOOD: This query type is performing well."
        elif total > 0:
            performance_level = "neutral"
        
        return {
            "thumbs_up": up_count,
            "thumbs_down": down_count,
            "total_feedback": total,
            "performance_level": performance_level,
            "warning": warning,
            "success_rate": (up_count / total * 100) if total > 0 else 0
        }
    
    def get_similar_successful_queries(self, question: str, limit: int = 3) -> List[Dict]:
        """Get similar queries that received positive feedback"""
        successful = [
            entry for entry in self.feedback_data
            if entry['feedback'] == 'up'
        ]
        
        # Simple similarity: check for common words
        question_words = set(question.lower().split())
        
        scored = []
        for entry in successful:
            entry_words = set(entry['question'].lower().split())
            similarity = len(question_words & entry_words) / len(question_words | entry_words)
            if similarity > 0.3:  # At least 30% similarity
                scored.append((similarity, entry))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [entry for _, entry in scored[:limit]]
    
    def get_failed_patterns(self) -> List[Dict]:
        """Get query patterns that consistently fail"""
        failed = []
        for question, scores in self.query_scores.items():
            if scores['down'] >= 2:
                failed.append({
                    "question_pattern": question,
                    "thumbs_down": scores['down'],
                    "thumbs_up": scores['up'],
                    "total": scores['total']
                })
        
        failed.sort(reverse=True, key=lambda x: x['thumbs_down'])
        return failed
    
    def get_overall_stats(self) -> Dict:
        """Get overall feedback statistics"""
        total_up = sum(s['up'] for s in self.query_scores.values())
        total_down = sum(s['down'] for s in self.query_scores.values())
        total = total_up + total_down
        
        return {
            "total_feedback": total,
            "thumbs_up": total_up,
            "thumbs_down": total_down,
            "success_rate": (total_up / total * 100) if total > 0 else 0,
            "unique_queries": len(self.query_scores),
            "critical_queries": len([s for s in self.query_scores.values() if s['down'] >= 3]),
            "excellent_queries": len([s for s in self.query_scores.values() if s['up'] >= 3])
        }

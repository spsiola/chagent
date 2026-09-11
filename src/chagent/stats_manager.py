import os
import sqlite3
import datetime
from typing import List, Dict, Any, Optional

class StatsManager:
    def __init__(self, db_path: str = "data/stats/llm_stats.db"):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize schema
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT,
                    model TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    duration_ms INTEGER,
                    cache_hit BOOLEAN
                )
            """)
            conn.commit()

    def record_stat(self, session_id: str, provider: str, model: str, 
                    prompt_tokens: int, completion_tokens: int, total_tokens: int, 
                    duration_ms: int, cache_hit: bool = False):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO llm_stats (
                        session_id, provider, model, prompt_tokens, 
                        completion_tokens, total_tokens, duration_ms, cache_hit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, provider, model, prompt_tokens, completion_tokens, total_tokens, duration_ms, cache_hit))
                conn.commit()
        except Exception as e:
            print(f"Failed to record LLM stat: {e}")

    def get_session_stats(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM llm_stats WHERE session_id = ? ORDER BY timestamp DESC
                """, (session_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Failed to fetch LLM stats: {e}")
            return []

    def get_all_stats(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM llm_stats ORDER BY timestamp DESC LIMIT 1000
                """)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Failed to fetch all LLM stats: {e}")
            return []

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """For read-only access by the agent native tool."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Basic protection for read-only (though a proper permission system is better)
                if any(verb in query.upper() for verb in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]):
                    raise ValueError("Only SELECT queries are allowed.")
                
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            return [{"error": str(e)}]

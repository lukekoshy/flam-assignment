"""Database module for job persistence and state management."""
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

class Database:
    """SQLite database manager for job queue."""
    
    def __init__(self, db_path: str = "jobs.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    command TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    worker_id TEXT,
                    last_error TEXT,
                    next_retry_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def enqueue(self, job_data: Dict[str, Any]) -> bool:
        """Add a new job to the queue."""
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        id, command, state, attempts, max_retries,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_data["id"],
                        job_data["command"],
                        "pending",
                        0,
                        job_data.get("max_retries", 3),
                        now,
                        now
                    )
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_jobs(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """List jobs, optionally filtered by state."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM jobs"
            params = []
            
            if state:
                query += " WHERE state = ?"
                params.append(state)
                
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_job_state(self, job_id: str, state: str, error: Optional[str] = None,
                        worker_id: Optional[str] = None, increment_attempts: bool = False) -> bool:
        """Update job state and related fields."""
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                query = """
                    UPDATE jobs SET
                        state = ?,
                        updated_at = ?,
                        worker_id = ?,
                        last_error = ?
                """
                params = [state, now, worker_id, error]
                
                if increment_attempts:
                    query += ", attempts = attempts + 1"
                    
                query += " WHERE id = ?"
                params.append(job_id)
                
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error:
                return False

    def fetch_and_lock_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Fetch next available job and lock it to a worker."""
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # First try pending jobs
            cursor = conn.execute(
                """
                SELECT * FROM jobs 
                WHERE state = 'pending'
                   OR (state = 'failed' 
                       AND attempts < max_retries 
                       AND (next_retry_at IS NULL OR next_retry_at <= ?))
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (now,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            job = dict(row)
            
            # Lock the job
            conn.execute(
                """
                UPDATE jobs SET
                    state = 'processing',
                    worker_id = ?,
                    updated_at = ?
                WHERE id = ? AND (state = 'pending' OR state = 'failed')
                """,
                (worker_id, now, job["id"])
            )
            conn.commit()
            
            return job

    def set_next_retry(self, job_id: str, retry_at: str) -> bool:
        """Set the next retry time for a failed job."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    "UPDATE jobs SET next_retry_at = ? WHERE id = ?",
                    (retry_at, job_id)
                )
                conn.commit()
                return True
            except sqlite3.Error:
                return False

    def move_to_dlq(self, job_id: str, error: str) -> bool:
        """Move a job to the dead letter queue."""
        return self.update_job_state(
            job_id=job_id,
            state="dead",
            error=error,
            worker_id=None
        )

    def retry_dlq_job(self, job_id: str) -> bool:
        """Move a job from DLQ back to pending state."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    """
                    UPDATE jobs SET
                        state = 'pending',
                        attempts = 0,
                        worker_id = NULL,
                        last_error = NULL,
                        next_retry_at = NULL,
                        updated_at = ?
                    WHERE id = ? AND state = 'dead'
                    """,
                    (datetime.now(timezone.utc).isoformat(), job_id)
                )
                conn.commit()
                return True
            except sqlite3.Error:
                return False

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM config WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else default

    def set_config(self, key: str, value: Any) -> bool:
        """Set a configuration value."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO config (key, value)
                    VALUES (?, ?)
                    """,
                    (key, json.dumps(value))
                )
                conn.commit()
                return True
            except sqlite3.Error:
                return False
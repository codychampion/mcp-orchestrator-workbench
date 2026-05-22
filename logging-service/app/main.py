"""
Centralized Logging Service for MCP Orchestrator
Captures all LLM calls, responses, and system logs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import sqlite3
import json
import os

app = FastAPI(title="MCP Logging Service")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path
DB_PATH = os.getenv("LOG_DB_PATH", "/app/data/logs.db")

# Initialize database
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # LLM calls table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            service TEXT NOT NULL,
            model TEXT,
            prompt TEXT NOT NULL,
            response TEXT,
            tokens_used INTEGER,
            duration_ms REAL,
            status TEXT NOT NULL,
            error TEXT,
            metadata TEXT,
            session_id TEXT,
            user_query TEXT
        )
    """)

    # System logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            service TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            session_id TEXT,
            trace_id TEXT
        )
    """)

    # Workflow executions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflow_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            workflow_id TEXT NOT NULL,
            node_id TEXT,
            event_type TEXT NOT NULL,
            data TEXT,
            status TEXT,
            session_id TEXT
        )
    """)

    # User feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            feedback_type TEXT NOT NULL,
            rating TEXT NOT NULL,
            session_id TEXT,
            data TEXT,
            user_query TEXT,
            tool_calls TEXT,
            execution_data TEXT
        )
    """)

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_timestamp ON llm_calls(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_session ON llm_calls(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sys_timestamp ON system_logs(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sys_level ON system_logs(level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_session ON workflow_executions(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON user_feedback(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_session ON user_feedback(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_rating ON user_feedback(rating)")

    conn.commit()
    conn.close()
    print(f"[Logging Service] Database initialized at {DB_PATH}")

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db()

# Pydantic models
class LLMCallLog(BaseModel):
    service: str
    model: Optional[str] = None
    prompt: str
    response: Optional[str] = None
    tokens_used: Optional[int] = None
    duration_ms: Optional[float] = None
    status: str = "success"
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    user_query: Optional[str] = None

class SystemLog(BaseModel):
    level: str  # INFO, WARNING, ERROR, DEBUG
    service: str
    message: str
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None

class WorkflowLog(BaseModel):
    workflow_id: str
    node_id: Optional[str] = None
    event_type: str
    data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    session_id: Optional[str] = None

class UserFeedbackLog(BaseModel):
    feedback_type: str
    rating: str  # positive, negative, correction
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    user_query: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    execution_data: Optional[Dict[str, Any]] = None

# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "logging-service"}

@app.post("/logs/llm")
async def log_llm_call(log: LLMCallLog):
    """Log an LLM call and response"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO llm_calls
            (timestamp, service, model, prompt, response, tokens_used, duration_ms, status, error, metadata, session_id, user_query)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            log.service,
            log.model,
            log.prompt,
            log.response,
            log.tokens_used,
            log.duration_ms,
            log.status,
            log.error,
            json.dumps(log.metadata) if log.metadata else None,
            log.session_id,
            log.user_query
        ))

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"status": "logged", "id": log_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log LLM call: {str(e)}")

@app.post("/logs/system")
async def log_system_event(log: SystemLog):
    """Log a system event"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO system_logs
            (timestamp, level, service, message, details, session_id, trace_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            log.level,
            log.service,
            log.message,
            json.dumps(log.details) if log.details else None,
            log.session_id,
            log.trace_id
        ))

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"status": "logged", "id": log_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log system event: {str(e)}")

@app.post("/logs/workflow")
async def log_workflow_event(log: WorkflowLog):
    """Log a workflow execution event"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO workflow_executions
            (timestamp, workflow_id, node_id, event_type, data, status, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            log.workflow_id,
            log.node_id,
            log.event_type,
            json.dumps(log.data) if log.data else None,
            log.status,
            log.session_id
        ))

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"status": "logged", "id": log_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log workflow event: {str(e)}")

@app.post("/logs/feedback")
async def log_user_feedback(log: UserFeedbackLog):
    """Log user feedback (thumbs up/down)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_feedback
            (timestamp, feedback_type, rating, session_id, data, user_query, tool_calls, execution_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            log.feedback_type,
            log.rating,
            log.session_id,
            json.dumps(log.data) if log.data else None,
            log.user_query,
            json.dumps(log.tool_calls) if log.tool_calls else None,
            json.dumps(log.execution_data) if log.execution_data else None
        ))

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"status": "logged", "id": log_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log user feedback: {str(e)}")

@app.get("/logs/llm")
async def get_llm_logs(
    limit: int = 100,
    offset: int = 0,
    session_id: Optional[str] = None,
    service: Optional[str] = None,
    status: Optional[str] = None
):
    """Retrieve LLM call logs"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM llm_calls WHERE 1=1"
        params = []

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if service:
            query += " AND service = ?"
            params.append(service)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Get total count
        count_query = "SELECT COUNT(*) FROM llm_calls WHERE 1=1"
        count_params = []
        if session_id:
            count_query += " AND session_id = ?"
            count_params.append(session_id)
        if service:
            count_query += " AND service = ?"
            count_params.append(service)
        if status:
            count_query += " AND status = ?"
            count_params.append(status)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]

        logs = []
        for row in rows:
            log = dict(row)
            if log['metadata']:
                log['metadata'] = json.loads(log['metadata'])
            logs.append(log)

        conn.close()

        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")

@app.get("/logs/system")
async def get_system_logs(
    limit: int = 100,
    offset: int = 0,
    level: Optional[str] = None,
    service: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Retrieve system logs"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM system_logs WHERE 1=1"
        params = []

        if level:
            query += " AND level = ?"
            params.append(level)
        if service:
            query += " AND service = ?"
            params.append(service)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Get total count
        count_query = "SELECT COUNT(*) FROM system_logs WHERE 1=1"
        count_params = []
        if level:
            count_query += " AND level = ?"
            count_params.append(level)
        if service:
            count_query += " AND service = ?"
            count_params.append(service)
        if session_id:
            count_query += " AND session_id = ?"
            count_params.append(session_id)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]

        logs = []
        for row in rows:
            log = dict(row)
            if log['details']:
                log['details'] = json.loads(log['details'])
            logs.append(log)

        conn.close()

        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")

@app.get("/logs/workflow/{workflow_id}")
async def get_workflow_logs(workflow_id: str):
    """Retrieve logs for a specific workflow execution"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM workflow_executions
            WHERE workflow_id = ?
            ORDER BY timestamp ASC
        """, (workflow_id,))

        rows = cursor.fetchall()

        logs = []
        for row in rows:
            log = dict(row)
            if log['data']:
                log['data'] = json.loads(log['data'])
            logs.append(log)

        conn.close()

        return {"workflow_id": workflow_id, "logs": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve workflow logs: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get logging statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # LLM stats
        cursor.execute("SELECT COUNT(*) FROM llm_calls")
        total_llm_calls = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM llm_calls WHERE status = 'success'")
        successful_llm_calls = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(duration_ms) FROM llm_calls WHERE duration_ms IS NOT NULL")
        avg_duration = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(tokens_used) FROM llm_calls WHERE tokens_used IS NOT NULL")
        total_tokens = cursor.fetchone()[0] or 0

        # System logs stats
        cursor.execute("SELECT COUNT(*) FROM system_logs")
        total_system_logs = cursor.fetchone()[0]

        cursor.execute("SELECT level, COUNT(*) FROM system_logs GROUP BY level")
        logs_by_level = {row[0]: row[1] for row in cursor.fetchall()}

        # Workflow stats
        cursor.execute("SELECT COUNT(DISTINCT workflow_id) FROM workflow_executions")
        total_workflows = cursor.fetchone()[0]

        conn.close()

        return {
            "llm": {
                "total_calls": total_llm_calls,
                "successful_calls": successful_llm_calls,
                "failed_calls": total_llm_calls - successful_llm_calls,
                "avg_duration_ms": round(avg_duration, 2),
                "total_tokens": total_tokens
            },
            "system_logs": {
                "total": total_system_logs,
                "by_level": logs_by_level
            },
            "workflows": {
                "total_executions": total_workflows
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.delete("/logs/clear")
async def clear_logs(confirm: bool = False):
    """Clear all logs (requires confirmation)"""
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to clear logs")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM llm_calls")
        cursor.execute("DELETE FROM system_logs")
        cursor.execute("DELETE FROM workflow_executions")

        conn.commit()
        conn.close()

        return {"status": "success", "message": "All logs cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)

import os
import json
from typing import Any, Dict, Optional
from pathlib import Path
from fastapi import HTTPException, status
from datetime import datetime

# centralized logging + decorator import
from logging_config import get_logger, log_exceptions
logger = get_logger(__name__)

# If you have helper functions that can raise, add @log_exceptions above them.
# Example:
# @log_exceptions
# def some_helper(...):
#     ...existing code...

class RequestSimulator:
    """Utility class to simulate HTTP requests for service functions"""
    def __init__(self, json_data: Dict[str, Any]):
        self._json = json_data

    async def json(self) -> Dict[str, Any]:
        return self._json

async def validate_session(session_id: str, active_sessions: Dict) -> str:
    """Validate session and return user_id. Checks both in-memory and database."""
    if not session_id:
        logger.warning("Session validation failed: No session_id provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid session"
        )
    
    # First check in-memory sessions (fast path)
    if session_id in active_sessions:
        logger.debug(f"Session found in memory: {session_id[:20]}...")
        return active_sessions[session_id]["user_id"]
    
    # Fallback to database check (for sessions that survived server restart)
    logger.debug(f"Session not in memory, checking database: {session_id[:20]}...")
    try:
        from db_manager import get_session
        session_data = await get_session(session_id)
        if session_data and session_data.get("user_id"):
            logger.info(f"Session found in database, re-populating cache: {session_id[:20]}...")
            # Re-populate in-memory cache
            active_sessions[session_id] = {
                "user_id": session_data["user_id"],
                "created_at": session_data.get("created_at", datetime.utcnow().isoformat())
            }
            return session_data["user_id"]
        else:
            logger.warning(f"Session not found in database: {session_id[:20]}...")
    except Exception as e:
        logger.error(f"Error validating session from database: {e}")
    
    logger.warning(f"Session validation failed for: {session_id[:20]}...")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Session expired or invalid. Please log in again."
    )

def ensure_upload_dir(user_id: str, thread_id: str, source_id: str, base_dir: Path) -> Path:
    """Ensure upload directory exists and return path"""
    # Convert to Path if it's a string
    if isinstance(base_dir, str):
        base_dir = Path(base_dir)
    upload_dir = base_dir / user_id / thread_id / source_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir

async def handle_service_error(func: callable, *args, **kwargs) -> Dict[str, Any]:
    """Generic error handler for service functions"""
    try:
        return await func(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service error in {func.__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service error: {str(e)}"
        )
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

async def validate_session(session_id: str) -> str:
    """Validate session and return user_id. Reads exclusively from MongoDB.

    Safe for Vercel Lambda — no in-memory state that resets on cold-start.
    """
    if not session_id:
        logger.warning("Session validation failed: No session_id provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid session"
        )

    try:
        from db_manager import get_session
        session_data = await get_session(session_id)
        if session_data and session_data.get("active") and session_data.get("user_id"):
            logger.debug(f"Session validated from DB: {session_id[:20]}...")
            return session_data["user_id"]
        else:
            logger.warning(f"Session not found or inactive in DB: {session_id[:20]}...")
    except Exception as e:
        logger.error(f"Error validating session from database: {e}")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Session expired or invalid. Please log in again."
    )

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
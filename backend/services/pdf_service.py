from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from pathlib import Path
import shutil
from datetime import datetime

from config import Settings, get_settings
from .exceptions import InvalidSessionError, ThreadNotFoundError
from .utils import validate_session, ensure_upload_dir
from db_manager import (
    add_source_to_chat_session,
    add_filename_to_uploaded_list,
    update_chat_session_field,
    get_chat_session_by_id,
    create_chat_session_in_db,
    get_user_chat_session_list,
    get_user_chat_session_count,
    mark_chat_session_as_deleted,
    rename_chat_session_title
)
import uuid
from logging_config import get_logger, log_exceptions
from callbacks import LoggingCallbackHandler

logger = get_logger(__name__)
router = APIRouter(tags=["PDF Operations"])

@router.post("/session")
@log_exceptions
async def create_chat_session(
    session_id: str = Form(...),
    settings: Settings = Depends(get_settings)
):
    """Create a new chat session"""
    logger.info(f"Creating new chat session for session: {session_id}")
    
    try:
        user_id = await validate_session(session_id)
        chat_session_id = str(uuid.uuid4())
        
        new_chat_session = {
            "chat_session_id": chat_session_id,
            "user_id": user_id,
            "title": "New Chat",
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
            "sources": []
        }
        
        # Database write — use async db_manager (Motor)
        await create_chat_session_in_db(new_chat_session)
        
        return JSONResponse(
            status_code=200,
            content={
                "chat_session_id": chat_session_id,
                "title": "New Chat"
            }
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@router.get("/session/{chat_session_id}")
@log_exceptions
async def get_chat_session(
    chat_session_id: str,
    session_id: str,
    settings: Settings = Depends(get_settings)
):
    """Get chat session details including updated title"""
    logger.info(f"Fetching chat session: {chat_session_id}")
    
    try:
        user_id = await validate_session(session_id)
        chat_session_data = await get_chat_session_by_id(chat_session_id, user_id)
        
        if not chat_session_data:
            raise ThreadNotFoundError()
        
        # Strip non-serialisable MongoDB _id
        chat_session_data.pop("_id", None)

        return JSONResponse(
            status_code=200,
            content={
                "chat_session_id": chat_session_id,
                "title": chat_session_data.get("title", "New Chat"),
                "created_at": chat_session_data.get("created_at"),
                "updated_at": chat_session_data.get("updated_at"),
                "messages": chat_session_data.get("messages", []),
                "sources": [
                    {
                        "source_id": s.get("source_id"),
                        "filename": s.get("filename"),
                        "filepath": s.get("filepath"),
                        "uploaded_at": s.get("uploaded_at"),
                        "related_questions": s.get("related_questions", []),
                        "mindmap": s.get("mindmap"),
                    }
                    for s in chat_session_data.get("sources", [])
                ],
                "message_count": len(chat_session_data.get("messages", [])),
                "source_count": len(chat_session_data.get("sources", [])),
            }
        )
    except ThreadNotFoundError:
        raise HTTPException(status_code=404, detail="Chat session not found")
    except Exception as e:
        logger.error(f"Error fetching chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat session")

@router.post("/upload")
@log_exceptions
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    chat_session_id: str = Form(...),
    settings: Settings = Depends(get_settings)
):
    """Handle PDF upload with improved error handling and logging"""
    logger.info(f"Processing PDF upload: {file.filename} for chat session {chat_session_id}")
    
    try:
        logger.debug(f"Validating session: {session_id[:20]}...")
        user_id = await validate_session(session_id)
        logger.debug(f"Session valid, user_id: {user_id}")
        
        logger.debug(f"Fetching chat session: {chat_session_id}")
        chat_session_data = await get_chat_session_by_id(chat_session_id, user_id)
        
        if not chat_session_data:
            logger.error(f"Chat session not found: {chat_session_id}")
            raise ThreadNotFoundError()

        source_id = str(uuid.uuid4())
        logger.debug(f"Creating upload directory for source: {source_id}")
        upload_dir = ensure_upload_dir(
            user_id, chat_session_id, source_id, settings.UPLOAD_DIR
        )
        
        file_path = upload_dir / file.filename
        logger.debug(f"Saving file to: {file_path}")
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        new_source = {
            "source_id": source_id,
            "filename": file.filename,
            "filepath": str(file_path),
            "related_questions": [],
            "mindmap": {"path": None, "chat_messages": []},
            "podcast": {"data": None}
        }

        # DB writes — use async db_manager functions
        await add_source_to_chat_session(chat_session_id, new_source)
        await add_filename_to_uploaded_list(chat_session_id, file.filename)

        # Update chat session title if needed
        new_title = None
        if not chat_session_data.get('sources') and chat_session_data.get('title') == "New Chat":
            new_title = file.filename
            await update_chat_session_field(chat_session_id, {'title': new_title})
            logger.info(f"Updated chat session title to: {new_title}")

        logger.info(f"PDF upload successful: {file.filename}")
        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "new_source": new_source,
                "chat_session_id": chat_session_id,
                "new_title": new_title
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like ThreadNotFoundError)
        raise
    except Exception as e:
        logger.error(f"PDF upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/sessions")
@log_exceptions
async def get_all_sessions(
    session_id: str,
    limit: int = 50,
):
    """Get all chat sessions for the authenticated user, sorted by most recent."""
    user_id = await validate_session(session_id)
    sessions = await get_user_chat_session_list(user_id, limit=limit)
    total = await get_user_chat_session_count(user_id)

    for s in sessions:
        s.pop("_id", None)

    return {
        "sessions": sessions,
        "total": total,
        "limit": limit,
    }


@router.delete("/session/{chat_session_id}")
@log_exceptions
async def delete_chat_session(
    chat_session_id: str,
    session_id: str,
):
    """Soft-delete a chat session (marks as deleted, data is retained)."""
    user_id = await validate_session(session_id)
    chat_session = await get_chat_session_by_id(chat_session_id, user_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    await mark_chat_session_as_deleted(chat_session_id)
    logger.info(f"Chat session deleted: {chat_session_id} by user: {user_id}")
    return {"message": "Chat session deleted successfully", "chat_session_id": chat_session_id}


@router.patch("/session/{chat_session_id}/rename")
@log_exceptions
async def rename_session(
    chat_session_id: str,
    session_id: str,
    new_title: str,
):
    """Rename a chat session."""
    user_id = await validate_session(session_id)
    chat_session = await get_chat_session_by_id(chat_session_id, user_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    await rename_chat_session_title(chat_session_id, new_title)
    logger.info(f"Chat session renamed: {chat_session_id} -> '{new_title}'")
    return {"message": "Session renamed successfully", "chat_session_id": chat_session_id, "new_title": new_title}

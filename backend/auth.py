import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from fastapi import APIRouter, HTTPException, status, Depends
# run_in_threadpool is not used here after DB helpers migrated to async
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import bcrypt
from logging_config import get_logger, log_exceptions
from db_manager import (
    create_user,
    get_user_by_id,
    update_user_last_login,
    create_session as create_session_in_db,
    get_session as get_session_from_db,
    COLLECTION_USERS
)

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# NOTE: We're using stateful sessions only (no JWT). Session persistence is
# handled by the `sessions` collection via `db_manager`.

# Active sessions in memory (for quick lookup)
# In production, use Redis or persistent store
active_sessions: Dict[str, Dict[str, Any]] = {}

# ============================================================================
# PYDANTIC MODELS
#
# NOTE: This project uses Pydantic v2 style validators. The old `validator`
# decorator from Pydantic v1 is deprecated — we use `field_validator` for
# single-field validation and `model_validator` for cross-field checks (e.g.
# password/confirm_password equality).
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Pydantic v2: use field_validator for single-field validation
    @field_validator("username")
    def validate_username(cls, v):
        """Validate username format"""
        # allow alphanumeric characters or underscore or hyphen
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError("Username can only contain alphanumeric characters, underscores, and hyphens")
        return v

    # Confirm password must match password — this is a cross-field validation
    @model_validator(mode="after")
    def validate_passwords_match(cls, model):
        """Ensure passwords match (model-level validator)"""
        if getattr(model, "password", None) is not None and getattr(model, "confirm_password", None) != model.password:
            raise ValueError("Passwords do not match")
        return model


class UserLoginRequest(BaseModel):
    """User login request model"""
    email: EmailStr
    password: str


class UserLoginResponse(BaseModel):
    """User login response model (session-only auth)"""
    status: str
    message: str
    user_id: str
    session_id: str


class UserRegisterResponse(BaseModel):
    """User registration response model"""
    status: str
    message: str
    user_id: str
    email: str
    username: str


class UserLogoutRequest(BaseModel):
    """Logout request — session_id in body, not query string"""
    session_id: str


class ChangePasswordRequest(BaseModel):
    """Change password request body"""
    session_id: str
    old_password: str
    new_password: str
    confirm_password: str


class UserProfileResponse(BaseModel):
    """User profile response model"""
    user_id: str
    email: str
    username: str
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    created_at: str
    last_login: Optional[str]
    active: bool


class UserProfileUpdateRequest(BaseModel):
    """Update user profile request body"""
    session_id: str
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None


# ============================================================================
# API KEY MASKING
# ============================================================================

def mask_api_key(key: Optional[str]) -> Optional[str]:
    """Return a masked version of an API key for safe display in the UI.
    Shows the first 6 and last 4 characters, replacing the middle with '...'.
    Returns None if the key is not set."""
    if not key:
        return None
    if len(key) <= 10:
        return "***"
    return f"{key[:6]}...{key[-4:]}"


# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

# JWT token functions removed — session-only authentication is used


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

async def create_session(user_id: str) -> str:
    """Create a new session for user (stores both in-memory and database)"""
    session_id = str(uuid.uuid4())
    
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
        "active": True
    }
    
    # Store in memory for fast access
    active_sessions[session_id] = session_data
    
    # Store in database for persistence (non-blocking)
    try:
        # db_manager.create_session is async (Motor) so call directly
        await create_session_in_db(session_data)
    except Exception as e:
        logger.error(f"Failed to store session in database: {e}")
    
    logger.info(f"Session created: {session_id} for user: {user_id}")
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session details"""
    return active_sessions.get(session_id)


async def validate_session(session_id: str) -> Optional[str]:
    """Validate session and return user_id if valid.

    Checks in-memory cache first (fast path), then falls back to MongoDB.
    This ensures sessions survive Lambda cold starts on Vercel.
    """
    # Fast path: in-memory cache
    session = active_sessions.get(session_id)
    if session is not None:
        if not session.get("active"):
            logger.warning(f"Session is inactive: {session_id}")
            return None
        session["last_activity"] = datetime.utcnow().isoformat()
        return session.get("user_id")

    # Slow path: look up in MongoDB (handles server restarts + Lambda cold starts)
    logger.debug(f"Session not in memory, checking DB: {session_id[:20]}...")
    try:
        from db_manager import get_session as get_session_from_db
        session_data = await get_session_from_db(session_id)
        if session_data and session_data.get("user_id"):
            # Re-populate in-memory cache for subsequent requests in same invocation
            active_sessions[session_id] = {
                "user_id": session_data["user_id"],
                "active": True,
                "created_at": session_data.get("created_at", datetime.utcnow().isoformat()),
                "last_activity": datetime.utcnow().isoformat(),
            }
            logger.info(f"Session restored from DB: {session_id[:20]}...")
            return session_data["user_id"]
    except Exception as e:
        logger.error(f"Error validating session from DB: {e}")

    logger.warning(f"Session not found: {session_id}")
    return None


def invalidate_session(session_id: str) -> None:
    """Invalidate/logout session"""
    if session_id in active_sessions:
        active_sessions[session_id]["active"] = False
        logger.info(f"Session invalidated: {session_id}")


def invalidate_all_user_sessions(user_id: str) -> None:
    """Invalidate all sessions for a user (logout all devices)"""
    invalidated_count = 0
    for session_id, session_data in active_sessions.items():
        if session_data.get("user_id") == user_id:
            session_data["active"] = False
            invalidated_count += 1
    
    logger.info(f"Invalidated {invalidated_count} sessions for user: {user_id}")


def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """Remove old inactive sessions"""
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
    sessions_to_remove = []
    
    for session_id, session_data in active_sessions.items():
        if not session_data.get("active"):
            created_at = datetime.fromisoformat(session_data.get("created_at", ""))
            if created_at < cutoff_time:
                sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del active_sessions[session_id]
    
    if sessions_to_remove:
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
    
    return len(sessions_to_remove)


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

router = APIRouter(tags=["Authentication"])


@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
@log_exceptions
async def register(request: UserRegisterRequest):
    """Register a new user"""
    logger.info(f"Registration attempt for email: {request.email}")
    
    try:
        # Normalize inputs (trim whitespace and lowercase email) and check if user already exists
        from db_manager import _db_manager
        # Use async Motor client directly
        email_clean = request.email.strip().lower()
        username_clean = request.username.strip()
        existing_user = await _db_manager.db[COLLECTION_USERS].find_one({
            "$or": [
                {"email": email_clean},
                {"username": username_clean}
            ]
        })
        
        if existing_user:
            if existing_user.get("email") == email_clean:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken"
                )
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(request.password.strip())
        
        user_doc = {
            "user_id": user_id,
            "email": email_clean,
            "username": username_clean,
            "password_hash": hashed_password,
            "openai_api_key": request.openai_api_key,
            "gemini_api_key": request.gemini_api_key,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_login": None,
            "active": True
        }
        
        # Use async Motor insert
        await _db_manager.db[COLLECTION_USERS].insert_one(user_doc)
        logger.info(f"User registered successfully: {user_id}")
        
        return UserRegisterResponse(
            status="success",
            message="User registered successfully",
            user_id=user_id,
            email=request.email,
            username=request.username
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=UserLoginResponse)
@log_exceptions
async def login(request: UserLoginRequest):
    """Login user and create session"""
    logger.info(f"Login attempt for email: {request.email}")
    
    try:
        # Normalize inputs and find user by email
        from db_manager import _db_manager
        email_clean = request.email.strip().lower()
        password_clean = request.password.strip()
        user = await _db_manager.db[COLLECTION_USERS].find_one({"email": email_clean})
        
        if not user:
            logger.warning(f"Login failed: user not found for email {email_clean}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.get("active"):
            logger.warning(f"Login failed: user account inactive {user.get('user_id')}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Verify password
        if not verify_password(password_clean, user.get("password_hash", "")):
            logger.warning(f"Login failed: invalid password for email {email_clean}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create session (session-only authentication)
        user_id = user.get("user_id")
        session_id = await create_session(user_id)
        
        # Update last login (async DB update)
        await update_user_last_login(user_id)
        
        logger.info(f"User logged in successfully: {user_id}")
        
        return UserLoginResponse(
            status="success",
            message="Login successful",
            user_id=user_id,
            session_id=session_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# /refresh endpoint removed — using session-only authentication


@router.post("/logout")
@log_exceptions
async def logout(request: UserLogoutRequest):
    """Logout user and invalidate session"""
    session_id = request.session_id
    logger.info(f"Logout attempt for session: {session_id}")
    
    try:
        # Validate session exists
        user_id = await validate_session(session_id)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Invalidate session
        invalidate_session(session_id)
        logger.info(f"User logged out: {user_id}")
        
        return {
            "status": "success",
            "message": "Logged out successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all")
@log_exceptions
async def logout_all(request: UserLogoutRequest):
    """Logout from all devices (invalidate all user sessions)"""
    session_id = request.session_id
    logger.info(f"Logout all attempt for session: {session_id}")
    
    try:
        # Validate session exists
        user_id = await validate_session(session_id)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Invalidate all user sessions
        invalidate_all_user_sessions(user_id)
        logger.info(f"User logged out from all devices: {user_id}")
        
        return {
            "status": "success",
            "message": "Logged out from all devices successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout all error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/profile", response_model=UserProfileResponse)
@log_exceptions
async def get_profile(session_id: str):
    """Get user profile information — session_id passed as query param (GET request, no body).
    For higher security, consider using an Authorization header instead."""
    logger.info(f"Profile request for session: {session_id}")
    
    try:
        # Validate session
        user_id = await validate_session(session_id)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Get user from database
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserProfileResponse(
            user_id=user.get("user_id"),
            email=user.get("email"),
            username=user.get("username"),
            openai_api_key=mask_api_key(user.get("openai_api_key")),
            gemini_api_key=mask_api_key(user.get("gemini_api_key")),
            created_at=user.get("created_at"),
            last_login=user.get("last_login"),
            active=user.get("active")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


# /verify-token endpoint removed — session-based auth does not use tokens


@router.post("/change-password")
@log_exceptions
async def change_password(request: ChangePasswordRequest):
    """Change user password"""
    session_id = request.session_id
    old_password = request.old_password
    new_password = request.new_password
    confirm_password = request.confirm_password
    logger.info(f"Password change attempt for session: {session_id}")
    
    try:
        # Validate session
        user_id = await validate_session(session_id)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        # Validate new passwords match
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match"
            )
        
        # Validate password length
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters"
            )
        
        # Get user and verify old password
        user = await get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not verify_password(old_password, user.get("password_hash", "")):
            logger.warning(f"Password change failed: invalid old password for {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid old password"
            )
        
        # Update password
        from db_manager import _db_manager
        hashed_new_password = hash_password(new_password)

        # Run update in threadpool
        await _db_manager.db[COLLECTION_USERS].update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "password_hash": hashed_new_password,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"Password changed for user: {user_id}")
        
        return {
            "status": "success",
            "message": "Password changed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


# ============================================================================
# PROFILE OPERATIONS
# ============================================================================

@router.patch("/profile")
@log_exceptions
async def update_profile(request: UserProfileUpdateRequest):
    """Update user API keys"""
    session_id = request.session_id
    logger.info(f"Profile update attempt for session: {session_id}")
    
    try:
        user_id = await validate_session(session_id)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
            
        from db_manager import _db_manager
        
        update_data = {}
        # We only update if the payload explicitly provides a string (even an empty string to clear it)
        if request.openai_api_key is not None:
            update_data["openai_api_key"] = request.openai_api_key
        if request.gemini_api_key is not None:
            update_data["gemini_api_key"] = request.gemini_api_key
            
        if not update_data:
            return {"status": "success", "message": "No fields to update"}
            
        update_data["updated_at"] = datetime.utcnow().isoformat()
            
        await _db_manager.db[COLLECTION_USERS].update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        
        logger.info(f"Profile updated for user: {user_id}")
        return {"status": "success", "message": "Profile updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/health")
async def auth_health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len([s for s in active_sessions.values() if s.get("active")])
    }


logger.info("auth.py loaded successfully")

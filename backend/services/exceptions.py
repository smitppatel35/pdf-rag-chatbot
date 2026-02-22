from fastapi import HTTPException, status
from typing import Optional

# Add centralized logging
from logging_config import get_logger, log_exceptions
logger = get_logger(__name__)

class PDFBotException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)

class InvalidSessionError(PDFBotException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid session"
        )

class ThreadNotFoundError(PDFBotException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )

class SourceNotFoundError(PDFBotException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
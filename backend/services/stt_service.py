from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from typing import Dict, Any, Optional
import logging
from services.local_audio import transcribe_audio_local
from config import get_settings

# centralized logging + decorator import
from logging_config import get_logger, log_exceptions
logger = get_logger(__name__)

router = APIRouter(tags=["Speech-to-Text Operations"])

class STTResponse(BaseModel):
    status: str
    transcript: Optional[str]

@router.post("/", response_model=STTResponse)
@log_exceptions
async def transcribe_audio(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings)
) -> STTResponse:
    logger.info(f"Transcribing audio file: {file.filename}")

    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        if settings.STT_API_URL == "local_stt":
            transcript = transcribe_audio_local(temp_path)
            logger.info("Audio transcription completed.")
            return STTResponse(status="success", transcript=transcript)
        else:
            raise HTTPException(status_code=501, detail="Remote STT API not implemented.")
    except Exception as e:
        logger.error(f"Error in audio transcription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during STT processing.")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
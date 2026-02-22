# from fastapi import APIRouter, Depends, HTTPException, status
# from typing import Dict, Any, Optional
# import logging
# import base64
# from services.local_audio import generate_podcast_audio_local
# from config import get_settings

# # centralized logging + decorator import
# from logging_config import get_logger, log_exceptions
# logger = get_logger(__name__)

# router = APIRouter(tags=["Podcast Operations"])

# class PodcastRequest(BaseModel):
#     session_id: str
#     chat_session_id: str
#     source_id: str
#     script: str

# class PodcastResponse(BaseModel):
#     status: str
#     audio_base64: Optional[str]
#     chat_session_id: str
#     source_id: str

# """ Disabled podcast endpoint as per user request
# # @router.post("/", response_model=PodcastResponse)
# # @log_exceptions
# # async def generate_podcast(
# #     request: PodcastRequest,
# #     settings: Settings = Depends(get_settings)
# # ) -> PodcastResponse:
#     logger.info(f"Generating podcast for chat session: {request.chat_session_id}, source: {request.source_id}")

#     output_filepath = f"podcast_{request.chat_session_id}_{request.source_id}.wav"
#     try:
#         if settings.PODCAST_API_URL == "local_podcast":
#             generate_podcast_audio_local(request.script, output_filepath)
#             with open(output_filepath, "rb") as audio_file:
#                 audio_bytes = audio_file.read()
#             audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
#             logger.info("Podcast audio generated and encoded to Base64.")
#             return PodcastResponse(
#                 status="success",
#                 audio_base64=audio_base64,
#                 chat_session_id=request.chat_session_id,
#                 source_id=request.source_id
#             )
#         else:
#             raise HTTPException(status_code=501, detail="Remote podcast API not implemented.")
#     except Exception as e:
#         logger.error(f"Error in podcast generation: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="An internal error occurred while generating the podcast audio.")
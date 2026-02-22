import os
import pyttsx3
from faster_whisper import WhisperModel
import speech_recognition as sr
from logging_config import get_logger, log_exceptions

logger = get_logger(__name__)

# ============================================================================
# AUDIO CONFIGURATION
# ============================================================================

# Text-to-Speech (TTS) Settings
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")
TTS_RATE = int(os.getenv("TTS_RATE", "150"))      # Words per minute
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "0.9")) # Volume level (0.0 to 1.0)

# Speech-to-Text (STT) Settings
STT_ENGINE = os.getenv("STT_ENGINE", "faster_whisper")
STT_MODEL = os.getenv("STT_MODEL", "base")  # Whisper model size: tiny, base, small, medium, large

# ============================================================================
# TEXT-TO-SPEECH FUNCTIONS
# ============================================================================

@log_exceptions(logger)
def generate_tts_audio(text: str, output_path: str):
    """
    Generate speech audio from text using pyttsx3 (local TTS).
    
    Args:
        text: Text to convert to speech
        output_path: Path where the audio file will be saved
    """
    try:
        engine = pyttsx3.init()
        
        # Apply TTS configuration
        engine.setProperty('rate', TTS_RATE)
        engine.setProperty('volume', TTS_VOLUME)
        
        logger.debug(f"Generating TTS audio with rate={TTS_RATE}, volume={TTS_VOLUME}")
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        logger.info(f"TTS audio saved to {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Failed to generate TTS audio: {e}")
        raise

# ============================================================================
# SPEECH-TO-TEXT FUNCTIONS
# ============================================================================

@log_exceptions(logger)
def transcribe_audio_local(audio_path: str) -> str:
    """
    Transcribe audio to text using faster-whisper (local STT).
    
    Args:
        audio_path: Path to the audio file to transcribe
        
    Returns:
        Transcribed text
    """
    try:
        logger.debug(f"Transcribing audio from {audio_path} using {STT_MODEL} model")
        
        # Load Whisper model
        model = WhisperModel(STT_MODEL, device="auto", compute_type="auto")
        
        # Transcribe
        segments, info = model.transcribe(audio_path)
        
        # Combine all segments
        text = " ".join([segment.text for segment in segments])
        
        logger.info(f"Successfully transcribed {len(segments)} segments from {audio_path}")
        return text
    
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        raise

# ============================================================================
# PODCAST GENERATION
# ============================================================================

@log_exceptions(logger)
def generate_podcast_audio_local(script: str, output_path: str) -> str:
    """
    Generate podcast audio from script using local TTS.
    
    Args:
        script: Podcast script text
        output_path: Path where the podcast audio file will be saved
        
    Returns:
        Path to the generated audio file
    """
    try:
        logger.info(f"Generating podcast audio from script ({len(script)} characters)")
        return generate_tts_audio(script, output_path)
    
    except Exception as e:
        logger.error(f"Failed to generate podcast audio: {e}")
        raise
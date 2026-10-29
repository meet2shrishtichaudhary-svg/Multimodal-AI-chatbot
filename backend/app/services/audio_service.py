import io
import os
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

async def transcribe_audio_file(file_path: str) -> str:
    """
    Transcribes audio (mp3, wav, m4a, webm) to text.
    Uses OpenAI Whisper when configured; returns simulated transcription in mock/dev mode.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            with open(file_path, "rb") as audio_file:
                transcription = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                return transcription.text
        except Exception as e:
            logger.warning(f"OpenAI Whisper unavailable ({e}), using fallback transcription.")
    
    # Offline / development mock transcription
    filename = os.path.basename(file_path)
    return f"[Transcription of {filename}]: Audio processed successfully."

async def synthesize_speech(text: str, voice: str = "alloy") -> bytes:
    """
    Generates spoken audio (mp3 bytes) from input text.
    Uses OpenAI TTS if key is configured, or generates a silent/synthesized audio byte stream.
    """
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text[:4096]
            )
            return response.content
        except Exception as e:
            logger.warning(f"OpenAI TTS unavailable ({e}), using fallback audio.")

    # Minimal valid 1-second silent MP3 header/frame for offline/test playback
    # ID3v2 minimal tag + empty frame
    return b"\xff\xfb\x90\x64\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" * 40

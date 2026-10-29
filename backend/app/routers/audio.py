import os
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Response
from app.services.audio_service import transcribe_audio_file, synthesize_speech
from app.core.config import settings
from app.core.security import validate_uploaded_file

router = APIRouter(prefix="/audio", tags=["Audio"])

class SpeakRequest(BaseModel):
    text: str
    voice: str = "alloy"
    language: str = "en"

class TranscribeResponse(BaseModel):
    text: str

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribes uploaded audio (speech-to-text).
    Supports .mp3, .wav, .m4a, .webm, .ogg.
    """
    ext = validate_uploaded_file(file)
    if ext not in [".mp3", ".wav", ".m4a", ".webm", ".ogg"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: '{ext}'. Supported: .mp3, .wav, .m4a, .webm, .ogg"
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_path = os.path.join(settings.UPLOAD_DIR, f"audio_{uuid.uuid4().hex}{ext}")

    try:
        with open(temp_path, "wb") as buffer:
            while chunk := await file.read(1024 * 64):
                buffer.write(chunk)

        transcription = await transcribe_audio_file(temp_path)
        return TranscribeResponse(text=transcription)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio transcription error: {str(e)}"
        )
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@router.post("/speak")
async def generate_speech(req: SpeakRequest):
    """
    Synthesizes speech audio from text (text-to-speech) and streams MP3 bytes.
    """
    if not req.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty.")

    try:
        audio_bytes = await synthesize_speech(text=req.text, voice=req.voice)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'inline; filename="speech.mp3"'}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis error: {str(e)}"
        )

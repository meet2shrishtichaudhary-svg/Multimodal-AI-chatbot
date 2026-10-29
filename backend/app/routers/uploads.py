import os
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Attachment
from app.schemas.chat import AttachmentDTO
from app.core.config import settings
from app.core.security import get_auth_context, validate_uploaded_file

router = APIRouter(prefix="/uploads", tags=["Uploads"])

@router.post("", response_model=AttachmentDTO)
async def upload_attachment(
    file: UploadFile = File(...),
    conversation_id: str = Form(None),
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Upload and register an attachment (image, document, or audio file).
    Validates file extension and size limit before storing.
    """
    ext = validate_uploaded_file(file)

    # Classify attachment type
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
        attachment_type = "image"
    elif ext in [".mp3", ".wav", ".m4a", ".webm", ".ogg"]:
        attachment_type = "audio"
    else:
        attachment_type = "document"

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    file_size = 0
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 64):
            file_size += len(chunk)
            if file_size > max_bytes:
                buffer.close()
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
                )
            buffer.write(chunk)

    attachment = Attachment(
        conversation_id=conversation_id,
        file_name=file.filename,
        file_path=file_path,
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        attachment_type=attachment_type
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return attachment

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_auth_context
from app.services.image_service import generate_or_fetch_image

router = APIRouter(prefix="/image", tags=["Image Generation"])

class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=2, description="Image generation prompt")
    conversation_id: Optional[str] = None

class ImageGenerateResponse(BaseModel):
    prompt: str
    file_name: str
    image_url: str
    full_url: str
    mime_type: str
    format: str

@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image_endpoint(
    req: ImageGenerateRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Generate or fetch a high-quality visual/image based on a prompt.
    Supports AI Vector SVG and high-resolution visuals.
    """
    try:
        result = await generate_or_fetch_image(
            prompt=req.prompt,
            session_id=auth_ctx["session_id"],
            conv_id=req.conversation_id,
            db=db
        )
        return ImageGenerateResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image generation failed: {str(e)}"
        )


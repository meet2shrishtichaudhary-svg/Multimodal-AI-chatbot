from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.schemas.chat import MessageDTO

class ConversationSummaryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: int = 0

class ConversationDetailDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: List[MessageDTO] = []

class UpdateConversationTitleRequest(BaseModel):
    title: str

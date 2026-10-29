from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class AttachmentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_path: str
    mime_type: str
    file_size: int
    attachment_type: str
    created_at: datetime

class MessageDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    msg_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    attachments: List[AttachmentDTO] = Field(default_factory=list)
    created_at: datetime

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, description="User text prompt")
    enable_web_search: bool = False
    attachment_ids: Optional[List[str]] = Field(default_factory=list)
    persona: Optional[str] = "general"

class SourceCitation(BaseModel):
    title: str
    url: Optional[str] = None
    snippet: str
    source_type: str  # 'web' or 'document'
    document_title: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    user_message: MessageDTO
    assistant_message: MessageDTO
    citations: List[SourceCitation] = Field(default_factory=list)
    search_performed: bool = False
    rag_used: bool = False

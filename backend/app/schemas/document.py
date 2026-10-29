from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class KnowledgeDocumentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    title: str
    mime_type: str
    file_size: int
    total_chunks: int
    created_at: Optional[datetime] = None

class DocumentVersionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    version_number: int
    content: str
    change_summary: str
    created_at: Optional[datetime] = None

class DocumentWorkspaceDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latest_version: Optional[DocumentVersionDTO] = None
    versions: List[DocumentVersionDTO] = []

class DocumentCreateRequest(BaseModel):
    title: str = "Untitled Document"
    prompt: Optional[str] = None
    initial_content: Optional[str] = None

class DocumentEditRequest(BaseModel):
    instruction: str  # e.g., "Add a summary at the top", "Translate to Spanish", "Fix grammar"
    current_content: Optional[str] = None

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class MemoryCreateRequest(BaseModel):
    fact: str = Field(..., min_length=2, max_length=1000)
    category: str = Field(default="general", max_length=50)

class MemoryUpdateRequest(BaseModel):
    fact: Optional[str] = Field(default=None, min_length=2, max_length=1000)
    category: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None

class MemoryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    session_id: str
    fact: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class MemoryListResponse(BaseModel):
    memories: List[MemoryDTO]
    total: int


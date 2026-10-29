from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class RAGChunkMatch(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    text: str
    similarity: float
    metadata: Dict[str, Any] = {}

class RAGContextResponse(BaseModel):
    chunks: List[RAGChunkMatch]
    total_found: int
    is_sufficient: bool

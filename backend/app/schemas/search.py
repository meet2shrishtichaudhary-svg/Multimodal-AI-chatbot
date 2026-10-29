from typing import List, Optional
from pydantic import BaseModel

class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    provider: str

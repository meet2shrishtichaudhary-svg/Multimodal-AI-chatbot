from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class FeedbackCreateRequest(BaseModel):
    message_id: str
    rating: int = Field(..., ge=-1, le=1, description="1 for helpful/thumbs up, -1 for unhelpful/thumbs down")
    category: Optional[str] = Field(default="accuracy", max_length=50)
    comment: Optional[str] = Field(default=None, max_length=1000)

class FeedbackSummaryResponse(BaseModel):
    total_ratings: int
    positive_ratings: int
    negative_ratings: int
    satisfaction_rate_percent: float
    category_breakdown: Dict[str, int]


import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import Message, MessageFeedback
from app.schemas.feedback import FeedbackCreateRequest, FeedbackSummaryResponse
from app.core.security import get_auth_context

logger = logging.getLogger("mm_chatbot.feedback")

router = APIRouter(prefix="/feedback", tags=["Feedback & AI Evaluation"])

@router.post("", status_code=status.HTTP_201_CREATED)
def submit_message_feedback(
    req: FeedbackCreateRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Submits user feedback (+1 helpful / -1 unhelpful) with optional category and comment.
    """
    msg = db.query(Message).filter(Message.id == req.message_id).first()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found."
        )

    # Check for existing feedback on this message by user/session
    user_id = auth_ctx["user_id"]
    existing = db.query(MessageFeedback).filter(
        MessageFeedback.message_id == req.message_id,
        MessageFeedback.user_id == user_id if user_id else True
    ).first()

    if existing:
        existing.rating = req.rating
        existing.category = req.category or "accuracy"
        existing.comment = req.comment
        db.commit()
        db.refresh(existing)
        return {"message": "Feedback updated successfully.", "id": existing.id}

    feedback = MessageFeedback(
        message_id=req.message_id,
        user_id=user_id,
        rating=req.rating,
        category=req.category or "accuracy",
        comment=req.comment
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    logger.info(f"Feedback recorded for message {req.message_id}: rating={req.rating}, category={req.category}")
    return {"message": "Feedback recorded successfully.", "id": feedback.id}

@router.get("/summary", response_model=FeedbackSummaryResponse)
def get_feedback_summary(
    db: Session = Depends(get_db)
):
    """
    Returns aggregated quality feedback analytics.
    """
    all_feedback = db.query(MessageFeedback).all()
    total = len(all_feedback)
    positive = sum(1 for f in all_feedback if f.rating > 0)
    negative = sum(1 for f in all_feedback if f.rating < 0)
    rate = (positive / total * 100) if total > 0 else 100.0

    category_counts: Dict[str, int] = {}
    for f in all_feedback:
        cat = f.category or "other"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return FeedbackSummaryResponse(
        total_ratings=total,
        positive_ratings=positive,
        negative_ratings=negative,
        satisfaction_rate_percent=round(rate, 1),
        category_breakdown=category_counts
    )


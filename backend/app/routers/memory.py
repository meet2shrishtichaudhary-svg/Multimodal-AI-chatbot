from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import UserMemory
from app.schemas.memory import MemoryDTO, MemoryCreateRequest, MemoryUpdateRequest, MemoryListResponse
from app.core.security import get_auth_context
from app.services.memory_service import store_memory, retrieve_user_memories

router = APIRouter(prefix="/memory", tags=["Smart Conversational Memory"])

def _get_accessible_memory(db: Session, memory_id: str, auth_ctx: Dict[str, Any]) -> UserMemory:
    mem = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory fact not found.")

    if auth_ctx["user"]:
        if mem.user_id != auth_ctx["user_id"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory fact not found.")
    else:
        if mem.session_id != auth_ctx["session_id"] or mem.user_id is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory fact not found.")
    return mem

@router.get("", response_model=MemoryListResponse)
def list_user_memories(
    active_only: bool = False,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Retrieve stored conversational memories and preferences for the current user or guest session.
    """
    memories = retrieve_user_memories(db=db, auth_ctx=auth_ctx, active_only=active_only)
    return MemoryListResponse(
        memories=[MemoryDTO.model_validate(m) for m in memories],
        total=len(memories)
    )

@router.post("", response_model=MemoryDTO, status_code=status.HTTP_201_CREATED)
def create_user_memory(
    req: MemoryCreateRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Manually add a fact or preference for the AI to persistently remember.
    """
    memory = store_memory(
        db=db,
        auth_ctx=auth_ctx,
        fact=req.fact,
        category=req.category
    )
    return memory

@router.patch("/{memory_id}", response_model=MemoryDTO)
def update_user_memory(
    memory_id: str,
    req: MemoryUpdateRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Edit an existing memory or toggle its active/inactive status.
    """
    mem = _get_accessible_memory(db, memory_id, auth_ctx)
    if req.fact is not None:
        mem.fact = req.fact.strip()
    if req.category is not None:
        mem.category = req.category.strip()
    if req.is_active is not None:
        mem.is_active = req.is_active

    db.commit()
    db.refresh(mem)
    return mem

@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_memory(
    memory_id: str,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Delete a specific remembered fact.
    """
    mem = _get_accessible_memory(db, memory_id, auth_ctx)
    db.delete(mem)
    db.commit()
    return None

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_memories(
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Wipes all persistent memories for the user or session.
    """
    filter_cond = (
        (UserMemory.user_id == auth_ctx["user_id"])
        if auth_ctx["user_id"]
        else (UserMemory.session_id == auth_ctx["session_id"])
    )
    db.query(UserMemory).filter(filter_cond).delete()
    db.commit()
    return None


import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Conversation, Message
from app.schemas.conversation import ConversationSummaryDTO, ConversationDetailDTO, UpdateConversationTitleRequest
from app.core.security import get_auth_context

router = APIRouter(prefix="/conversations", tags=["Conversations"])

def _get_user_conversations_query(db: Session, auth_ctx: Dict[str, Any]):
    """
    Returns query filtered by user_id if logged in,
    or session_id (with user_id is None) if in guest mode.
    """
    if auth_ctx["user"]:
        return db.query(Conversation).filter(Conversation.user_id == auth_ctx["user_id"])
    return db.query(Conversation).filter(
        Conversation.session_id == auth_ctx["session_id"],
        Conversation.user_id.is_(None)
    )

def _get_accessible_conversation(db: Session, conversation_id: str, auth_ctx: Dict[str, Any]):
    """
    Verifies ownership of conversation for current user or guest.
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return None

    if auth_ctx["user"]:
        if conv.user_id == auth_ctx["user_id"]:
            return conv
        # If conversation was created in the active guest session, auto-claim it
        if conv.session_id == auth_ctx["session_id"] and conv.user_id is None:
            conv.user_id = auth_ctx["user_id"]
            db.commit()
            db.refresh(conv)
            return conv
        return None
    else:
        if conv.session_id == auth_ctx["session_id"] and conv.user_id is None:
            return conv
        return None

@router.get("", response_model=List[ConversationSummaryDTO])
def list_conversations(
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    List all conversations belonging to the current user (or guest session).
    """
    conversations = (
        _get_user_conversations_query(db, auth_ctx)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    results = []
    for conv in conversations:
        results.append(ConversationSummaryDTO(
            id=conv.id,
            session_id=conv.session_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at or conv.created_at,
            message_count=len(conv.messages)
        ))
    return results

@router.get("/{conversation_id}", response_model=ConversationDetailDTO)
def get_conversation(
    conversation_id: str,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Retrieve full conversation history, ensuring tenant isolation.
    """
    conv = _get_accessible_conversation(db, conversation_id, auth_ctx)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied."
        )
    return conv

@router.patch("/{conversation_id}", response_model=ConversationSummaryDTO)
def update_conversation_title(
    conversation_id: str,
    req: UpdateConversationTitleRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    conv = _get_accessible_conversation(db, conversation_id, auth_ctx)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    conv.title = req.title.strip()
    db.commit()
    db.refresh(conv)
    return ConversationSummaryDTO(
        id=conv.id,
        session_id=conv.session_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at or conv.created_at,
        message_count=len(conv.messages)
    )

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    conv = _get_accessible_conversation(db, conversation_id, auth_ctx)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    db.delete(conv)
    db.commit()
    return None

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_conversations(
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Clears all conversations belonging to the current user or guest session.
    """
    conversations = _get_user_conversations_query(db, auth_ctx).all()
    for c in conversations:
        db.delete(c)
    db.commit()
    return None

@router.get("/{conversation_id}/export")
def export_conversation(
    conversation_id: str,
    format: str = "markdown",
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Exports a conversation history into Markdown, JSON, or Plain Text.
    """
    conv = _get_accessible_conversation(db, conversation_id, auth_ctx)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    safe_title = "".join(c for c in (conv.title or "conversation") if c.isalnum() or c in ("-", "_", " ")).strip().replace(" ", "_")

    if format.lower() == "json":
        data = {
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "citations": m.msg_metadata.get("citations", []) if m.msg_metadata else []
                }
                for m in conv.messages
            ]
        }
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.json"'}
        )

    elif format.lower() == "txt":
        lines = [f"=== {conv.title.upper()} ===", f"Exported: {conv.created_at}\n"]
        for m in conv.messages:
            lines.append(f"[{m.role.upper()}]:\n{m.content}\n")
        return Response(
            content="\n".join(lines),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.txt"'}
        )

    else:
        # Default to clean formatted Markdown
        md_lines = [
            f"# {conv.title}",
            f"*Session export generated on {conv.updated_at or conv.created_at}*\n",
            "---",
            ""
        ]
        for m in conv.messages:
            role_header = "### 👤 You" if m.role == "user" else "### 🤖 Aura AI"
            md_lines.append(f"{role_header}\n\n{m.content}\n")
            if m.msg_metadata and m.msg_metadata.get("citations"):
                cites = m.msg_metadata["citations"]
                md_lines.append("**Sources Cited:**")
                for c in cites:
                    title = c.get("title") or c.get("document_title") or "Source"
                    url = c.get("url")
                    if url:
                        md_lines.append(f"- [{title}]({url})")
                    else:
                        md_lines.append(f"- {title}")
                md_lines.append("")
        return Response(
            content="\n".join(md_lines),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.md"'}
        )

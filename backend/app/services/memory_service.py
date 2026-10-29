import re
import logging
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import UserMemory

logger = logging.getLogger(__name__)

# Patterns for automatic fact extraction from conversation turns
MEMORY_EXTRACTION_PATTERNS = [
    (r"(?:please\s+)?remember\s+that\s+(.+)", "preference"),
    (r"(?:i\s+work\s+as|my\s+role\s+is|i\s+am\s+a)\s+([a-zA-Z0-9\s_-]{4,60})", "work"),
    (r"(?:i\s+prefer|my\s+preference\s+is)\s+(.+)", "preference"),
    (r"(?:my\s+tech\s+stack\s+is|i\s+use|we\s+build\s+with)\s+([a-zA-Z0-9\s,._-]{4,80})", "project"),
    (r"(?:i\s+live\s+in|i\s+am\s+based\s+in)\s+([a-zA-Z\s]{3,40})", "personal")
]

def auto_extract_memories(text: str) -> List[Tuple[str, str]]:
    """
    Scans user prompt for explicit memorable facts or preferences.
    Returns list of (fact_string, category).
    """
    extracted = []
    cleaned = text.strip()
    for pattern, category in MEMORY_EXTRACTION_PATTERNS:
        matches = re.finditer(pattern, cleaned, re.IGNORECASE)
        for m in matches:
            fact = m.group(1).strip().rstrip(".,!")
            if len(fact) >= 4 and len(fact) <= 250:
                extracted.append((fact, category))
    return extracted

def store_memory(
    db: Session,
    auth_ctx: Dict[str, Any],
    fact: str,
    category: str = "general"
) -> UserMemory:
    """
    Saves or deduplicates a user memory fact.
    """
    clean_fact = fact.strip()
    user_id = auth_ctx["user_id"]
    session_id = auth_ctx["session_id"]

    # Check for existing duplicate memory
    filter_cond = (
        (UserMemory.user_id == user_id)
        if user_id
        else (UserMemory.session_id == session_id)
    )
    existing = db.query(UserMemory).filter(
        filter_cond,
        UserMemory.fact == clean_fact
    ).first()

    if existing:
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    memory = UserMemory(
        user_id=user_id,
        session_id=session_id,
        fact=clean_fact,
        category=category,
        is_active=True
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    logger.info(f"Stored user memory for {user_id or session_id}: [{category}] {clean_fact[:40]}...")
    return memory

def retrieve_user_memories(
    db: Session,
    auth_ctx: Dict[str, Any],
    active_only: bool = True,
    limit: int = 15
) -> List[UserMemory]:
    """
    Retrieves stored memories for the user or session.
    """
    filter_cond = (
        (UserMemory.user_id == auth_ctx["user_id"])
        if auth_ctx["user_id"]
        else (UserMemory.session_id == auth_ctx["session_id"])
    )

    query = db.query(UserMemory).filter(filter_cond)
    if active_only:
        query = query.filter(UserMemory.is_active == True)

    return query.order_by(UserMemory.updated_at.desc()).limit(limit).all()

def format_memory_context(memories: List[UserMemory]) -> str:
    """
    Formats retrieved user memories into system prompt context block.
    """
    if not memories:
        return ""

    lines = [
        "--- USER PERSISTENT LONG-TERM MEMORY CONTEXT ---",
        "The following are verified facts and preferences about the user from previous interactions:"
    ]
    for mem in memories:
        lines.append(f"- [{mem.category}]: {mem.fact}")

    lines.append(
        "Directives for Memory Usage:\n"
        "1. Tailor explanations, coding styles, and tone to respect these user preferences.\n"
        "2. Do not recite this memory block back to the user unless they ask what you know about them.\n"
        "--- END USER PERSISTENT MEMORY CONTEXT ---"
    )
    return "\n".join(lines)


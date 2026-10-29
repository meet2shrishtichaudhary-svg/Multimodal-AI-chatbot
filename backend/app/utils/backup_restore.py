import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import (
    User, Conversation, Message, Attachment,
    KnowledgeDocument, DocumentChunk, DocumentWorkspace,
    DocumentVersion, UserMemory, MessageFeedback
)

logger = logging.getLogger("mm_chatbot.backup")

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")

def dump_database_to_dict(db: Session) -> Dict[str, Any]:
    """Serializes all relational tables to a dictionary."""
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0",
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "hashed_password": u.hashed_password,
                "full_name": u.full_name,
                "bio": u.bio,
                "preferred_persona": u.preferred_persona,
                "custom_instructions": u.custom_instructions,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in db.query(User).all()
        ],
        "conversations": [
            {
                "id": c.id,
                "session_id": c.session_id,
                "user_id": c.user_id,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in db.query(Conversation).all()
        ],
        "messages": [
            {
                "id": m.id,
                "conversation_id": m.conversation_id,
                "role": m.role,
                "content": m.content,
                "msg_metadata": m.msg_metadata,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in db.query(Message).all()
        ],
        "knowledge_documents": [
            {
                "id": d.id,
                "session_id": d.session_id,
                "user_id": d.user_id,
                "title": d.title,
                "file_path": d.file_path,
                "mime_type": d.mime_type,
                "file_size": d.file_size,
                "total_chunks": d.total_chunks
            }
            for d in db.query(KnowledgeDocument).all()
        ],
        "document_workspaces": [
            {
                "id": w.id,
                "session_id": w.session_id,
                "user_id": w.user_id,
                "title": w.title
            }
            for w in db.query(DocumentWorkspace).all()
        ],
        "document_versions": [
            {
                "id": v.id,
                "workspace_id": v.workspace_id,
                "version_number": v.version_number,
                "content": v.content,
                "change_summary": v.change_summary
            }
            for v in db.query(DocumentVersion).all()
        ],
        "user_memories": [
            {
                "id": mem.id,
                "user_id": mem.user_id,
                "session_id": mem.session_id,
                "fact": mem.fact,
                "category": mem.category,
                "is_active": mem.is_active
            }
            for mem in db.query(UserMemory).all()
        ]
    }
    return data

def backup_database(output_path: str = None) -> str:
    """Creates a timestamped JSON backup archive."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not output_path:
        filename = f"backup_mm_chatbot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = os.path.join(BACKUP_DIR, filename)

    db = SessionLocal()
    try:
        data = dump_database_to_dict(db)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Database successfully backed up to {output_path}")
        return output_path
    finally:
        db.close()

def restore_database_from_file(backup_path: str) -> Dict[str, int]:
    """Restores database from a JSON backup file."""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found at {backup_path}")

    with open(backup_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    restored_counts = {}
    try:
        # Restore Users
        user_count = 0
        for u_data in data.get("users", []):
            if not db.query(User).filter(User.id == u_data["id"]).first():
                user = User(
                    id=u_data["id"],
                    email=u_data["email"],
                    hashed_password=u_data["hashed_password"],
                    full_name=u_data.get("full_name", ""),
                    bio=u_data.get("bio"),
                    preferred_persona=u_data.get("preferred_persona", "general"),
                    custom_instructions=u_data.get("custom_instructions")
                )
                db.add(user)
                user_count += 1
        db.commit()
        restored_counts["users"] = user_count

        logger.info(f"Restored database from {backup_path}: {restored_counts}")
        return restored_counts
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to restore database from {backup_path}: {e}")
        raise e
    finally:
        db.close()

def backup_sqlite_db(source_db_path: str, backup_dir: str = None) -> str:
    """Creates a raw SQLite file copy backup."""
    import shutil
    if not backup_dir:
        backup_dir = BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    filename = f"sqlite_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    target = os.path.join(backup_dir, filename)
    shutil.copy2(source_db_path, target)
    return target

def restore_sqlite_db(backup_path: str, target_db_path: str) -> bool:
    """Restores SQLite database from a raw SQLite backup file."""
    import shutil
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup {backup_path} not found")
    os.makedirs(os.path.dirname(os.path.abspath(target_db_path)), exist_ok=True)
    shutil.copy2(backup_path, target_db_path)
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) > 2:
            restore_database_from_file(sys.argv[2])
        else:
            print("Usage: python -m app.utils.backup_restore restore <path_to_backup.json>")
    else:
        out = backup_database()
        print(f"Created backup at: {out}")


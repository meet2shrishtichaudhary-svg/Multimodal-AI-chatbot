import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from app.db.session import Base
from app.core.config import settings

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

class VectorType(TypeDecorator):
    """
    Hybrid Vector Type:
    Uses pgvector's native Vector(dim) when on PostgreSQL,
    and falls back to JSON format when on SQLite for tests/local mock.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 1536, *args, **kwargs):
        self.dim = dim
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON)

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return value
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return value
        return value

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    preferred_persona = Column(String(50), default="general")
    custom_instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    reset_token = Column(String(100), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="user", cascade="all, delete-orphan")
    document_workspaces = relationship("DocumentWorkspace", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    attachments = relationship("Attachment", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    msg_metadata = Column(JSON, default=dict)  # Stores sources, citations, model used
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message")

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, default=0)
    attachment_type = Column(String(20), nullable=False)  # 'image', 'document', 'audio'
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="attachments")
    message = relationship("Message", back_populates="attachments")

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="knowledge_documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(VectorType(settings.EMBEDDING_DIM), nullable=True)
    chunk_metadata = Column(JSON, default=dict)  # page number, section name
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("KnowledgeDocument", back_populates="chunks")

class DocumentWorkspace(Base):
    __tablename__ = "document_workspaces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), default="Untitled Document")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="document_workspaces")
    versions = relationship("DocumentVersion", back_populates="workspace", cascade="all, delete-orphan", order_by="DocumentVersion.version_number.desc()")

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("document_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    change_summary = Column(String(255), default="Initial draft")
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("DocumentWorkspace", back_populates="versions")

class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    fact = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="memories")

class MessageFeedback(Base):
    __tablename__ = "message_feedbacks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    rating = Column(Integer, nullable=False)  # 1 (helpful) or -1 (unhelpful)
    category = Column(String(50), nullable=True)  # 'accuracy', 'citation', 'hallucination', 'style'
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

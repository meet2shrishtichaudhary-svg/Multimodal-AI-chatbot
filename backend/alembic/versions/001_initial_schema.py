"""Initial schema with pgvector

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-15 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enable vector extension on PostgreSQL
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Conversations
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_session_id'), 'conversations', ['session_id'], unique=False)

    # Messages
    op.create_table(
        'messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('msg_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)

    # Attachments
    op.create_table(
        'attachments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=True),
        sa.Column('message_id', sa.String(length=36), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('attachment_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Knowledge Documents
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('total_chunks', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_documents_session_id'), 'knowledge_documents', ['session_id'], unique=False)

    # Document Chunks (with pgvector embedding column)
    vector_col = Vector(1536) if HAS_PGVECTOR else sa.JSON()
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('embedding', vector_col, nullable=True),
        sa.Column('chunk_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)

    # Document Workspaces
    op.create_table(
        'document_workspaces',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_workspaces_session_id'), 'document_workspaces', ['session_id'], unique=False)

    # Document Versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('change_summary', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['document_workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_versions_workspace_id'), 'document_versions', ['workspace_id'], unique=False)

def downgrade() -> None:
    op.drop_table('document_versions')
    op.drop_table('document_workspaces')
    op.drop_table('document_chunks')
    op.drop_table('knowledge_documents')
    op.drop_table('attachments')
    op.drop_table('messages')
    op.drop_table('conversations')

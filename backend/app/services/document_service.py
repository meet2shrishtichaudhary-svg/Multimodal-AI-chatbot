import logging
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.db.models import DocumentWorkspace, DocumentVersion
from app.services.llm_service import get_llm_provider
from app.utils.file_parsers import create_docx_file

logger = logging.getLogger(__name__)

DOCUMENT_SYSTEM_PROMPT = """
You are an expert document editor, technical writer, and drafting assistant.
When modifying or drafting documents:
1. Follow user instructions precisely (e.g. rewrite section, correct grammar, translate, summarize).
2. PRESERVE all existing parts of the document that were not requested to be changed.
3. Keep clean markdown formatting (headings, bullet points, clean paragraphs).
4. Return ONLY the complete revised document content. Do not include chat commentary or conversational filler outside the document text.
"""

async def create_document(
    db: Session,
    session_id: str,
    title: str,
    prompt: Optional[str] = None,
    initial_content: Optional[str] = None,
    user_id: Optional[str] = None
) -> Tuple[DocumentWorkspace, DocumentVersion]:
    """
    Creates a new DocumentWorkspace and initial DocumentVersion (v1).
    """
    if prompt and not initial_content:
        llm = get_llm_provider()
        messages = [
            {"role": "user", "content": f"Please draft a structured, professional document based on this prompt:\n\n{prompt}"}
        ]
        content = await llm.generate_response(messages=messages, system_prompt=DOCUMENT_SYSTEM_PROMPT)
        summary = f"Drafted from prompt: {prompt[:60]}..."
    else:
        content = initial_content or f"# {title}\n\nStart writing your document here..."
        summary = "Initial document creation"

    workspace = DocumentWorkspace(
        session_id=session_id,
        user_id=user_id,
        title=title or "Untitled Document"
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    version = DocumentVersion(
        workspace_id=workspace.id,
        version_number=1,
        content=content,
        change_summary=summary
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    return workspace, version

async def edit_document_content(
    db: Session,
    workspace: DocumentWorkspace,
    instruction: str,
    current_content: Optional[str] = None
) -> DocumentVersion:
    """
    Applies requested edits to an existing document version, generating a new revision (v+1).
    Preserves unchanged text and records a clear change summary.
    """
    # Find latest version
    latest_version = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.workspace_id == workspace.id)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )

    base_content = current_content or (latest_version.content if latest_version else "")
    next_version_num = (latest_version.version_number + 1) if latest_version else 1

    llm = get_llm_provider()
    messages = [
        {
            "role": "user",
            "content": (
                f"Here is the current document content:\n\n"
                f"```markdown\n{base_content}\n```\n\n"
                f"User Edit Instruction: {instruction}\n\n"
                "Please generate the complete updated document adhering strictly to the edit instruction. "
                "Preserve all unchanged sections intact."
            )
        }
    ]

    revised_content = await llm.generate_response(messages=messages, system_prompt=DOCUMENT_SYSTEM_PROMPT)

    new_version = DocumentVersion(
        workspace_id=workspace.id,
        version_number=next_version_num,
        content=revised_content,
        change_summary=f"Edit: {instruction[:80]}"
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    return new_version

def export_document_bytes(content: str, title: str, format_type: str) -> Tuple[bytes, str, str]:
    """
    Exports document content to requested format.
    Returns: (file_bytes, filename, media_type)
    """
    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip() or "document"
    fmt = format_type.lower()

    if fmt == "docx":
        data = create_docx_file(content=content, title=title)
        return data, f"{safe_title}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fmt == "md":
        data = content.encode("utf-8")
        return data, f"{safe_title}.md", "text/markdown"
    else:  # txt
        data = content.encode("utf-8")
        return data, f"{safe_title}.txt", "text/plain"

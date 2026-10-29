import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import KnowledgeDocument, DocumentChunk, DocumentWorkspace, DocumentVersion
from app.schemas.document import (
    KnowledgeDocumentDTO, DocumentWorkspaceDTO, DocumentVersionDTO,
    DocumentCreateRequest, DocumentEditRequest
)
from app.core.config import settings
from app.core.security import get_auth_context, validate_uploaded_file
from app.utils.file_parsers import extract_text_from_file
from app.services.rag_service import index_document_content, clear_rag_cache_for_session
from app.services.document_service import create_document, edit_document_content, export_document_bytes

router = APIRouter(prefix="/documents", tags=["Documents"])

def _get_accessible_kdoc(db: Session, document_id: str, auth_ctx: Dict[str, Any]):
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not doc:
        return None
    if auth_ctx["user"]:
        if doc.user_id == auth_ctx["user_id"]:
            return doc
        if doc.session_id == auth_ctx["session_id"] and doc.user_id is None:
            doc.user_id = auth_ctx["user_id"]
            db.commit()
            return doc
        return None
    else:
        if doc.session_id == auth_ctx["session_id"] and doc.user_id is None:
            return doc
        return None

def _get_accessible_ws(db: Session, workspace_id: str, auth_ctx: Dict[str, Any]):
    ws = db.query(DocumentWorkspace).filter(DocumentWorkspace.id == workspace_id).first()
    if not ws:
        return None
    if auth_ctx["user"]:
        if ws.user_id == auth_ctx["user_id"]:
            return ws
        if ws.session_id == auth_ctx["session_id"] and ws.user_id is None:
            ws.user_id = auth_ctx["user_id"]
            db.commit()
            return ws
        return None
    else:
        if ws.session_id == auth_ctx["session_id"] and ws.user_id is None:
            return ws
        return None

# --- Knowledge Base Endpoints ---

@router.post("/upload", response_model=KnowledgeDocumentDTO)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Uploads a document (PDF, DOCX, TXT, MD) to the knowledge base,
    extracts text, chunks it, generates vector embeddings, and stores in DB.
    """
    ext = validate_uploaded_file(file)
    if ext not in [".pdf", ".docx", ".txt", ".md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document format: '{ext}'. Supported formats: .pdf, .docx, .txt, .md"
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_filename = f"kb_{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    file_size = 0
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 64):
            file_size += len(chunk)
            buffer.write(chunk)

    # Extract text from file
    try:
        extracted_text, sections = extract_text_from_file(file_path)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from document: {str(e)}"
        )

    if not extracted_text.strip():
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document contains no readable text."
        )

    # Duplicate Document Detection
    dup_filter = (
        (KnowledgeDocument.user_id == auth_ctx["user_id"])
        if auth_ctx["user"]
        else (KnowledgeDocument.session_id == auth_ctx["session_id"])
    )
    existing_dup = db.query(KnowledgeDocument).filter(
        dup_filter,
        KnowledgeDocument.title == file.filename,
        KnowledgeDocument.file_size == file_size
    ).first()
    if existing_dup:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document '{file.filename}' with identical content is already indexed in your knowledge base."
        )

    # Create document record
    doc = KnowledgeDocument(
        session_id=auth_ctx["session_id"],
        user_id=auth_ctx["user_id"],
        title=file.filename,
        file_path=file_path,
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        total_chunks=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Index chunks with vector embeddings
    await index_document_content(
        db=db,
        document=doc,
        extracted_text=extracted_text,
        sections=sections
    )

    return doc

@router.get("", response_model=List[KnowledgeDocumentDTO])
def list_knowledge_documents(
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Lists all indexed knowledge base documents belonging to this user or session.
    """
    if auth_ctx["user"]:
        docs = (
            db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.user_id == auth_ctx["user_id"])
            .order_by(KnowledgeDocument.created_at.desc())
            .all()
        )
    else:
        docs = (
            db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.session_id == auth_ctx["session_id"], KnowledgeDocument.user_id.is_(None))
            .order_by(KnowledgeDocument.created_at.desc())
            .all()
        )
    return docs

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_document(
    document_id: str,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Deletes a knowledge document and cascades deletion of all its vector chunks.
    """
    doc = _get_accessible_kdoc(db, document_id, auth_ctx)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    db.delete(doc)
    db.commit()
    clear_rag_cache_for_session(auth_ctx["session_id"])
    return None

# --- Document Workspace Endpoints ---

@router.post("/workspace", response_model=DocumentWorkspaceDTO)
async def create_workspace_document(
    req: DocumentCreateRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Create a new editable document workspace, optionally drafting from a prompt.
    """
    workspace, initial_version = await create_document(
        db=db,
        session_id=auth_ctx["session_id"],
        title=req.title,
        prompt=req.prompt,
        initial_content=req.initial_content,
        user_id=auth_ctx["user_id"]
    )
    return DocumentWorkspaceDTO(
        id=workspace.id,
        session_id=workspace.session_id,
        title=workspace.title,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        latest_version=DocumentVersionDTO.model_validate(initial_version),
        versions=[DocumentVersionDTO.model_validate(initial_version)]
    )

@router.get("/workspace", response_model=List[DocumentWorkspaceDTO])
def list_workspaces(
    search: Optional[str] = None,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    List all workspaces for the current user or session, with optional title search.
    """
    query = db.query(DocumentWorkspace)
    if auth_ctx["user"]:
        query = query.filter(DocumentWorkspace.user_id == auth_ctx["user_id"])
    else:
        query = query.filter(DocumentWorkspace.session_id == auth_ctx["session_id"], DocumentWorkspace.user_id.is_(None))

    if search and search.strip():
        query = query.filter(DocumentWorkspace.title.ilike(f"%{search.strip()}%"))

    workspaces = query.order_by(DocumentWorkspace.updated_at.desc()).all()
    results = []
    for ws in workspaces:
        latest = ws.versions[0] if ws.versions else None
        results.append(DocumentWorkspaceDTO(
            id=ws.id,
            session_id=ws.session_id,
            title=ws.title,
            created_at=ws.created_at,
            updated_at=ws.updated_at,
            latest_version=DocumentVersionDTO.model_validate(latest) if latest else None,
            versions=[DocumentVersionDTO.model_validate(v) for v in ws.versions]
        ))
    return results

@router.patch("/workspace/{workspace_id}", response_model=DocumentWorkspaceDTO)
def rename_workspace(
    workspace_id: str,
    title: str,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Rename an existing document workspace.
    """
    ws = _get_accessible_ws(db, workspace_id, auth_ctx)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    ws.title = title.strip() or "Untitled Document"
    ws.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ws)
    latest = ws.versions[0] if ws.versions else None
    return DocumentWorkspaceDTO(
        id=ws.id,
        session_id=ws.session_id,
        title=ws.title,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        latest_version=DocumentVersionDTO.model_validate(latest) if latest else None,
        versions=[DocumentVersionDTO.model_validate(v) for v in ws.versions]
    )

@router.post("/workspace/{workspace_id}/restore/{version_number}", response_model=DocumentVersionDTO)
def restore_workspace_version(
    workspace_id: str,
    version_number: int,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Restores the content of a prior version as the latest new revision.
    """
    ws = _get_accessible_ws(db, workspace_id, auth_ctx)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    target_version = None
    for v in ws.versions:
        if v.version_number == version_number:
            target_version = v
            break

    if not target_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version number {version_number} does not exist in this workspace."
        )

    new_version_num = max([v.version_number for v in ws.versions], default=0) + 1
    new_version = DocumentVersion(
        workspace_id=ws.id,
        version_number=new_version_num,
        content=target_version.content,
        change_summary=f"Restored from revision {version_number}"
    )
    db.add(new_version)
    ws.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(new_version)
    return DocumentVersionDTO.model_validate(new_version)

@router.get("/workspace/{workspace_id}/diff")
def compare_workspace_versions(
    workspace_id: str,
    from_version: int,
    to_version: int,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Computes a text unified diff comparison between two versions.
    """
    import difflib
    ws = _get_accessible_ws(db, workspace_id, auth_ctx)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    v1 = next((v for v in ws.versions if v.version_number == from_version), None)
    v2 = next((v for v in ws.versions if v.version_number == to_version), None)
    if not v1 or not v2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both specified versions do not exist.")

    diff_lines = list(difflib.unified_diff(
        v1.content.splitlines(keepends=True),
        v2.content.splitlines(keepends=True),
        fromfile=f"v{from_version}",
        tofile=f"v{to_version}"
    ))

    return {
        "workspace_id": ws.id,
        "from_version": from_version,
        "to_version": to_version,
        "diff": "".join(diff_lines),
        "has_changes": len(diff_lines) > 0
    }

@router.get("/workspace/{workspace_id}", response_model=DocumentWorkspaceDTO)
def get_workspace(
    workspace_id: str,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    ws = _get_accessible_ws(db, workspace_id, auth_ctx)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    latest = ws.versions[0] if ws.versions else None
    return DocumentWorkspaceDTO(
        id=ws.id,
        session_id=ws.session_id,
        title=ws.title,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        latest_version=DocumentVersionDTO.model_validate(latest) if latest else None,
        versions=[DocumentVersionDTO.model_validate(v) for v in ws.versions]
    )

@router.post("/workspace/{workspace_id}/edit", response_model=DocumentVersionDTO)
async def edit_workspace(
    workspace_id: str,
    req: DocumentEditRequest,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    ws = _get_accessible_ws(db, workspace_id, auth_ctx)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    new_version = await edit_document_content(
        db=db,
        workspace=ws,
        instruction=req.instruction,
        current_content=req.current_content
    )
    return DocumentVersionDTO.model_validate(new_version)

@router.get("/workspace/{workspace_id}/download")
def download_workspace(
    workspace_id: str,
    format: str = "docx",
    auth_ctx: Dict[str, Any] = Depends(get_auth_context),
    db: Session = Depends(get_db)
):
    """
    Downloads the latest revision in the requested format (.docx, .md, .txt).
    """
    ws = _get_accessible_ws(db, workspace_id, auth_ctx)
    if not ws or not ws.versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace or document version not found.")

    latest = ws.versions[0]
    data, filename, media_type = export_document_bytes(
        content=latest.content,
        title=ws.title,
        format_type=format
    )

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

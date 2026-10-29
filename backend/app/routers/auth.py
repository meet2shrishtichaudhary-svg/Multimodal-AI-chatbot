import os
import secrets
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User, Conversation, KnowledgeDocument, DocumentWorkspace, Attachment
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, AuthResponse, UserDTO,
    UserProfileUpdateRequest, ChangePasswordRequest, PasswordResetRequest,
    PasswordResetConfirm, AuthMessageResponse
)
from app.core.security import (
    hash_password, verify_password, create_access_token,
    get_current_user_required
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & User Profiles"])

def _claim_guest_records(db: Session, user_id: str, guest_session_id: str):
    """
    Transfers any conversations, knowledge base documents, and workspaces
    created during Guest Mode to the newly registered or logged-in user account.
    """
    if not guest_session_id:
        return
    try:
        # Transfer conversations
        convs = db.query(Conversation).filter(
            Conversation.session_id == guest_session_id,
            Conversation.user_id.is_(None)
        ).all()
        for c in convs:
            c.user_id = user_id

        # Transfer knowledge documents
        kdocs = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.session_id == guest_session_id,
            KnowledgeDocument.user_id.is_(None)
        ).all()
        for kd in kdocs:
            kd.user_id = user_id

        # Transfer workspaces
        wspaces = db.query(DocumentWorkspace).filter(
            DocumentWorkspace.session_id == guest_session_id,
            DocumentWorkspace.user_id.is_(None)
        ).all()
        for w in wspaces:
            w.user_id = user_id

        db.commit()
        logger.info(f"Successfully claimed {len(convs)} guest conversations for user {user_id}")
    except Exception as e:
        logger.warning(f"Error transferring guest session records: {e}")
        db.rollback()

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    req: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Sign up a new user account with email, password, and optional full name.
    Automatically generates JWT token and optionally merges prior guest chat history.
    """
    normalized_email = req.email.strip().lower()

    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in."
        )

    hashed_pw = hash_password(req.password)
    user = User(
        email=normalized_email,
        hashed_password=hashed_pw,
        full_name=req.full_name.strip() if req.full_name else "",
        preferred_persona=req.preferred_persona or "general"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Claim prior guest conversations if guest_session_id provided
    if req.claim_guest_session_id:
        _claim_guest_records(db, user.id, req.claim_guest_session_id)

    token = create_access_token({"sub": user.id, "email": user.email})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserDTO.model_validate(user)
    )

@router.post("/login", response_model=AuthResponse)
def login_user(
    req: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user credentials, return JWT access token, and optionally claim guest history.
    """
    normalized_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact support."
        )

    if req.claim_guest_session_id:
        _claim_guest_records(db, user.id, req.claim_guest_session_id)

    token = create_access_token({"sub": user.id, "email": user.email})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserDTO.model_validate(user)
    )

@router.get("/me", response_model=UserDTO)
def get_current_user_profile(
    current_user: User = Depends(get_current_user_required)
):
    """
    Retrieve personal profile and settings for the authenticated user.
    """
    return current_user

@router.put("/profile", response_model=UserDTO)
@router.patch("/profile", response_model=UserDTO)
def update_user_profile(
    req: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Update personal profile attributes: display name, avatar, bio, preferred persona, custom instructions.
    """
    if req.full_name is not None:
        current_user.full_name = req.full_name.strip()
    if req.avatar_url is not None:
        current_user.avatar_url = req.avatar_url.strip()
    if req.bio is not None:
        current_user.bio = req.bio.strip()
    if req.preferred_persona is not None:
        current_user.preferred_persona = req.preferred_persona.strip()
    if req.custom_instructions is not None:
        current_user.custom_instructions = req.custom_instructions.strip()

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    return current_user

@router.post("/change-password", response_model=AuthMessageResponse)
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Change password for an authenticated session.
    """
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    current_user.hashed_password = hash_password(req.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return AuthMessageResponse(message="Password changed successfully.")

@router.post("/forgot-password", response_model=AuthMessageResponse)
def forgot_password(
    req: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Initiate password recovery. Generates a secure time-limited reset token.
    """
    normalized_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        # Return generic message to prevent account enumeration
        return AuthMessageResponse(message="If this email is registered, password reset instructions have been generated.")

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=2)
    db.commit()

    logger.info(f"Generated password reset token for {normalized_email}")
    return AuthMessageResponse(
        message="Password reset token generated successfully. Valid for 2 hours.",
        reset_token=token
    )

@router.post("/reset-password", response_model=AuthMessageResponse)
def reset_password(
    req: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Complete password reset using token and set a new password.
    """
    normalized_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not user.reset_token or user.reset_token != req.reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    if user.reset_token_expires_at and user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )

    user.hashed_password = hash_password(req.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    user.updated_at = datetime.utcnow()
    db.commit()

    return AuthMessageResponse(message="Your password has been reset successfully. You can now log in.")

@router.post("/logout", response_model=AuthMessageResponse)
def logout_user():
    """
    Log out of the active session.
    """
    return AuthMessageResponse(message="Successfully logged out.")

@router.delete("/me", response_model=AuthMessageResponse)
def delete_user_account(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Permanently delete the user account and all personal chats, documents, and files.
    """
    user_id = current_user.id
    user_email = current_user.email

    # 1. Clean up physical knowledge document files
    user_docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.user_id == user_id).all()
    for doc in user_docs:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete document file {doc.file_path}: {e}")

    # 2. Clean up physical attachment files in user conversations
    user_conv_ids = [c.id for c in db.query(Conversation.id).filter(Conversation.user_id == user_id).all()]
    if user_conv_ids:
        attachments = db.query(Attachment).filter(Attachment.conversation_id.in_(user_conv_ids)).all()
        for att in attachments:
            if att.file_path and os.path.exists(att.file_path):
                try:
                    os.remove(att.file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete attachment file {att.file_path}: {e}")

    # 3. Delete user row (cascades all related database rows)
    db.delete(current_user)
    db.commit()

    logger.info(f"User account {user_email} (ID: {user_id}) permanently deleted with all data.")
    return AuthMessageResponse(message="Account and all associated personal data have been permanently deleted.")

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import Header, HTTPException, UploadFile, status, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

def hash_password(password: str) -> str:
    """Hash plain password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Extracts current authenticated user if Authorization Bearer token is provided.
    If no token or token is invalid, returns None (enabling Guest Mode).
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1].strip()
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    from app.db.models import User
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user

def get_current_user_required(
    user = Depends(get_current_user_optional)
):
    """
    Enforces authentication. Raises 401 Unauthorized if user is not logged in.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

def get_session_id(x_session_id: str = Header(None, alias="X-Session-ID")) -> str:
    """
    Validates or extracts anonymous guest session identifier from HTTP headers.
    """
    if not x_session_id:
        return str(uuid.uuid4())

    cleaned = x_session_id.strip()
    if len(cleaned) < 8 or len(cleaned) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Session-ID header format. Must be between 8 and 128 characters."
        )
    return cleaned

def get_auth_context(
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unified authentication context:
    - If user is authenticated: session_id is tied to user.id, is_guest=False
    - If user is guest: session_id is from X-Session-ID header, is_guest=True
    """
    user = get_current_user_optional(authorization=authorization, db=db)
    if user:
        return {
            "user": user,
            "user_id": user.id,
            "session_id": f"usr_{user.id}",
            "is_guest": False
        }
    else:
        guest_sess = get_session_id(x_session_id)
        return {
            "user": None,
            "user_id": None,
            "session_id": guest_sess,
            "is_guest": True
        }

def validate_uploaded_file(file: UploadFile) -> str:
    """
    Validates file extension and basic safety checks.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    clean_name = sanitize_filename(file.filename)
    ext = os.path.splitext(clean_name)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not supported. Supported extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    return ext

def sanitize_filename(filename: str) -> str:
    """
    Removes path traversal components, null bytes, and unsafe characters from filenames.
    """
    import re
    # Remove null bytes and directory separators
    clean = filename.replace("\0", "").replace("/", "_").replace("\\", "_")
    # Neutralize consecutive dots (path traversal)
    import re
    clean = re.sub(r'\.{2,}', '_', clean)
    # Strip dangerous characters
    clean = re.sub(r'[^a-zA-Z0-9._-]', '_', clean)
    # Ensure not starting with dot
    clean = clean.lstrip(".")
    return clean or "upload_file"

def safe_join_upload_path(filename: str) -> str:
    """
    Safely joins a filename to the upload directory, guaranteeing
    the resolved path stays strictly within settings.UPLOAD_DIR.
    """
    safe_name = sanitize_filename(filename)
    abs_upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    target_path = os.path.abspath(os.path.join(abs_upload_dir, safe_name))

    if not target_path.startswith(abs_upload_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal attempt detected. File path rejected."
        )
    return target_path

def redact_sensitive_text(text: str) -> str:
    """
    Redacts sensitive credentials, JWTs, and API keys from logs and diagnostics.
    """
    import re
    if not text:
        return ""
    # Redact OpenAI, Gemini, JWT tokens
    redacted = re.sub(r'(sk-[a-zA-Z0-9_-]{20,})', '[REDACTED_API_KEY]', text)
    redacted = re.sub(r'(AIzaSy[a-zA-Z0-9_-]{25,})', '[REDACTED_API_KEY]', redacted)
    redacted = re.sub(r'(Bearer\s+)[a-zA-Z0-9._-]{30,}', r'\1[REDACTED_JWT]', redacted)
    redacted = re.sub(r'(password["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', r'\1[REDACTED_PASSWORD]\3', redacted, flags=re.IGNORECASE)
    return redacted

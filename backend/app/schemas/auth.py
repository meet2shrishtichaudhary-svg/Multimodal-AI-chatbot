from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, EmailStr

class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=4, max_length=255, description="User email address")
    password: str = Field(..., min_length=6, max_length=128, description="User password (min 6 chars)")
    full_name: Optional[str] = Field(default="", max_length=255)
    preferred_persona: Optional[str] = Field(default="general")
    claim_guest_session_id: Optional[str] = Field(default=None, description="Optional anonymous session ID to claim chat history from")

class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=4, max_length=255)
    password: str = Field(..., min_length=1)
    claim_guest_session_id: Optional[str] = Field(default=None, description="Optional guest session ID to merge conversations from")

class PasswordResetRequest(BaseModel):
    email: str = Field(..., min_length=4, max_length=255)

class PasswordResetConfirm(BaseModel):
    email: str = Field(..., min_length=4, max_length=255)
    reset_token: str = Field(..., min_length=6, max_length=100)
    new_password: str = Field(..., min_length=6, max_length=128)

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)

class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    bio: Optional[str] = Field(default=None)
    preferred_persona: Optional[str] = Field(default=None, max_length=50)
    custom_instructions: Optional[str] = Field(default=None, description="Custom prompt instructions for how the AI should tailor responses")

class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferred_persona: str
    custom_instructions: Optional[str] = None
    created_at: datetime

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserDTO

class AuthMessageResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


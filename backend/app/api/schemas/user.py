"""User-related Pydantic schemas"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., min_length=3, max_length=50, description="Username")


class UserCreate(UserBase):
    """Schema for user registration"""

    password: str = Field(..., min_length=8, description="User password")
    full_name: Optional[str] = Field(None, description="Full name")


class UserLogin(BaseModel):
    """Schema for user login"""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class UserResponse(UserBase):
    """Schema for user response"""

    id: int
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile"""

    research_interests: Optional[List[str]] = Field(None, description="Research interests")
    preferred_categories: Optional[List[str]] = Field(
        None, description="Preferred arXiv categories"
    )
    keywords: Optional[List[str]] = Field(None, description="Interest keywords")
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")


class Token(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data"""

    user_id: Optional[int] = None
    email: Optional[str] = None

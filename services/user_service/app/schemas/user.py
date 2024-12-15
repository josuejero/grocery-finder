# services/user_service/app/schemas/user.py
from typing import Optional
from pydantic import BaseModel, EmailStr
from .profile import UserProfile  # Import UserProfile from profile.py

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    full_name: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    preferences: Optional[dict] = None
    favorite_stores: Optional[list] = None

    class Config:
        from_attributes = True  # For Pydantic v2
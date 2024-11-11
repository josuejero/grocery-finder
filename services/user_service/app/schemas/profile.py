from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserProfile(UserBase):
    preferences: dict = {}
    favorite_stores: List[str] = []
    model_config = ConfigDict(from_attributes=True)

class UserPreferencesUpdate(BaseModel):
    preferences: dict
    model_config = ConfigDict(from_attributes=True)

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    favorite_stores: Optional[List[str]] = None
    model_config = ConfigDict(from_attributes=True)
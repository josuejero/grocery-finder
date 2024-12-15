# services/user_service/app/schemas/profile.py
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr

class UserProfile(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    preferences: Dict[str, Any] = {}
    favorite_stores: List[str] = []
    
    class Config:
        from_attributes = True

class UserPreferencesUpdate(BaseModel):
    preferences: Dict[str, Any]
    
    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
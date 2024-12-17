from typing import Optional
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class User(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(User):
    password: str

class LoginCredentials(BaseModel):
    username: str
    password: str
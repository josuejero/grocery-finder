from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: Optional[bool] = False

class User(UserBase):
    pass

class UserInDB(UserBase):
    hashed_password: str

class UserCreate(UserBase):
    password: str
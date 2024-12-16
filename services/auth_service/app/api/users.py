# services/auth_service/api/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import EmailStr
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.security import get_password_hash, get_current_user
from app.schemas.user import User, UserCreate
from app.db.mongodb import get_db
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=User)
async def register_user(user: UserCreate, db: AsyncIOMotorClient = Depends(get_db)):
    user_dict = user.dict()
    hashed_password = get_password_hash(user_dict.pop("password"))
    user_dict["hashed_password"] = hashed_password

    try:
        new_user = await db.users.insert_one(user_dict)
        created_user = await db.users.find_one({"_id": new_user.inserted_id})
        if created_user:
            created_user.pop("hashed_password", None)  # Remove hashed_password before returning
            return User(**created_user)
    except Exception as e:
        if "duplicate key error" in str(e):
            if "username" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            elif "email" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

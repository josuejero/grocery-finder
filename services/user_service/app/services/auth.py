from typing import Optional
import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import logger
from app.db.models import UserModel

settings = Settings()

async def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token"
        )

async def get_user_from_auth_service(token: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.AUTH_SERVICE_URL}/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            logger.error(f"Failed to get user from auth service: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error communicating with auth service: {e}")
        return None

def get_user_from_db(db: Session, username: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.username == username).first()

async def sync_user_from_auth(db: Session, username: str, token: str) -> Optional[UserModel]:
    logger.debug(f"Syncing user data for username: {username}")
    user = get_user_from_db(db, username)
    
    if not user:
        logger.debug("User not found in local DB, fetching from auth service")
        auth_user = await get_user_from_auth_service(token)
        
        if auth_user:
            try:
                user = UserModel(
                    username=auth_user["username"],
                    email=auth_user["email"],
                    full_name=auth_user.get("full_name"),
                    preferences={},
                    favorite_stores=[]
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.debug(f"Created new user from auth service, ID: {user.id}")
            except Exception as e:
                logger.error(f"Failed to create user from auth data: {e}")
                db.rollback()
                return None
    
    return user

async def validate_and_get_user(db: Session, token: str) -> Optional[UserModel]:
    try:
        payload = await verify_token(token)
        user = await sync_user_from_auth(db, payload["sub"], token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating and getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
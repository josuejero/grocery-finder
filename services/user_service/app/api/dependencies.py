from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import logger
from app.db.database import get_db
from app.db.models import UserModel  # Changed from app.models.user

settings = get_settings()

async def verify_token(token: str) -> dict:
    logger.debug(f"Verifying token: {token[:20]}...")
    if not token:
        logger.error("No token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            logger.error("Token payload missing username")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        logger.debug(f"Token verified for user: {username}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token"
        )

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserModel:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )

    try:
        token = authorization.split(" ")[1]
        payload = await verify_token(token)
        username: str = payload.get("sub")
        
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user
    except (IndexError, jwt.PyJWTError) as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
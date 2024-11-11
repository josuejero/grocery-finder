from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.db.database import get_db
from app.db.models import UserModel
from app.schemas.profile import UserProfile, UserPreferencesUpdate, UserProfileUpdate
from app.api.dependencies import get_current_user

settings = get_settings()
router = APIRouter(tags=["profiles"])

@router.get("/users/me", response_model=UserProfile)
async def get_user_profile(
    current_user: UserModel = Depends(get_current_user)
):
    return current_user

@router.put("/users/me", response_model=UserProfile)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        for field, value in profile_update.model_dump(exclude_unset=True).items():
            setattr(current_user, field, value)
        
        current_user.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(current_user)
        
        return current_user
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/users/me/preferences")
async def update_preferences(
    preferences: UserPreferencesUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        current_user.preferences = preferences.preferences
        current_user.updated_at = datetime.now(UTC)
        db.commit()
        return {
            "status": "success",
            "preferences": current_user.preferences
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def sync_user_from_auth(db: Session, username: str, token: str) -> UserModel:
    logger.debug(f"Syncing user data for username: {username}")
    user = db.query(UserModel).filter(UserModel.username == username).first()
    
    if not user:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.AUTH_SERVICE_URL}/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    auth_user = response.json()
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
                else:
                    logger.error(f"Failed to get user from auth service: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Auth service unavailable"
                    )
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to auth service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service unavailable"
            )
    
    return user


@router.post("/users/sync")
async def sync_user(
    username: str,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        # Verify token
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Get user from Auth service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.AUTH_SERVICE_URL}/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            auth_user = response.json()
            
        # Create or update user in User service
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            user = UserModel(
                username=auth_user["username"],
                email=auth_user["email"],
                full_name=auth_user.get("full_name"),
                preferences={},
                favorite_stores=[]
            )
            db.add(user)
        else:
            user.email = auth_user["email"]
            user.full_name = auth_user.get("full_name")
            
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"User sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
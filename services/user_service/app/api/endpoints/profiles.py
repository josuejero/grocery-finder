# services/user_service/app/api/endpoints/profiles.py

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.core.config import Settings
from app.core.logging import logger
from app.db.database import get_db
from app.db.models import UserModel
from app.schemas.profile import UserProfile, UserPreferencesUpdate, UserProfileUpdate
from app.api.dependencies import get_current_user, verify_token

settings = Settings()
router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def get_user_profile(
    current_user: UserModel = Depends(get_current_user)
):
    return current_user

@router.put("/me", response_model=UserProfile)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        for field, value in profile_update.model_dump(exclude_unset=True).items():
            setattr(current_user, field, value)
        
        current_user.updated_at = datetime.now(timezone.utc)
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

@router.put("/me/preferences")
async def update_preferences(
    preferences: UserPreferencesUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        current_user.preferences = preferences.preferences
        current_user.updated_at = datetime.now(timezone.utc)
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

@router.post("/sync", response_model=UserProfile)
async def sync_user(
    username: str,
    authorization: str = Depends(),
    db: Session = Depends(get_db)
):
    try:
        # Verify the token
        try:
            token = authorization.replace("Bearer ", "")
            payload = await verify_token(token)
            if payload.get("sub") != username:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Username mismatch with token"
                )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # First check if user already exists
        user = db.query(UserModel).filter(UserModel.username == username).first()
        
        if not user:
            # Get user data from Auth service
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{settings.AUTH_SERVICE_URL}/users/me",
                        headers={"Authorization": authorization}
                    )
                    response.raise_for_status()
                    auth_user = response.json()
                    
                    # Create new user in User service
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
                    logger.info(f"Created new user {username} through sync")
            except httpx.RequestError as e:
                logger.error(f"Failed to get user data from Auth service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to communicate with Auth service"
                )
            except Exception as e:
                logger.error(f"Failed to create user during sync: {e}")
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

import logging
import os
import sys
from datetime import datetime, UTC
import datetime as dt
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.exc import IntegrityError
from sqlalchemy import TypeDecorator
import json
import jwt
from jwt.exceptions import PyJWTError
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from contextlib import asynccontextmanager

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="User Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cf00a032a7d8943e4e569105b95087b382b31153c3d7aad6138a173da04f89f3")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

class CompatibleArray(TypeDecorator):
    impl = String

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_ARRAY(String))
        else:
            return dialect.type_descriptor(String)

    def process_bind_param(self, value, dialect):
        if dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        if dialect.name == 'postgresql':
            return value
        else:
            return json.loads(value) if value is not None else None

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    preferences = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))

    shopping_lists = relationship("ShoppingListModel", back_populates="user")
    favorite_stores = Column(CompatibleArray(String), default=[])

class ShoppingListModel(Base):
    __tablename__ = "shopping_lists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    items = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))

    user = relationship("UserModel", back_populates="shopping_lists")

class UserProfile(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    preferences: dict = {}
    favorite_stores: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class ShoppingList(BaseModel):
    name: str
    items: List[dict] = []
    model_config = ConfigDict(from_attributes=True)

class ShoppingListUpdate(BaseModel):
    name: Optional[str] = None
    items: Optional[List[dict]] = None
    is_active: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        logger.debug(f"Token verified for user: {username}")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except PyJWTError as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token"
        )

def get_user_from_db(db: Session, username: str):
    return db.query(UserModel).filter(UserModel.username == username).first()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully initialized database")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        logger.info("Shutting down...")

app.lifespan_context = lifespan

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    logger.debug(f"Incoming request: {request.method} {request.url}")
    if "authorization" in request.headers:
        logger.debug("Authorization header present")
    response = await call_next(request)
    logger.debug(f"Response status: {response.status_code}")
    return response

@app.get("/health")
async def health_check():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    finally:
        db.close()

@app.get("/users/me", response_model=UserProfile)
async def get_user_profile(payload: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user = get_user_from_db(db, payload["sub"])
    if not user:
        logger.error(f"User not found: {payload['sub']}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@app.put("/users/me", response_model=UserProfile)
async def update_user_profile(
    profile: UserProfile,
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user = get_user_from_db(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        for key, value in profile.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        user.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@app.post("/users/me/shopping-lists", response_model=ShoppingList)
async def create_shopping_list(
    shopping_list: ShoppingList,
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user = get_user_from_db(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        new_list = ShoppingListModel(
            user_id=user.id,
            name=shopping_list.name,
            items=shopping_list.items
        )
        db.add(new_list)
        db.commit()
        db.refresh(new_list)
        return new_list
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create shopping list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shopping list"
        )

@app.get("/users/me/shopping-lists", response_model=List[ShoppingList])
async def get_shopping_lists(
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user = get_user_from_db(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    lists = db.query(ShoppingListModel).filter(
        ShoppingListModel.user_id == user.id,
        ShoppingListModel.is_active == True
    ).all()
    return lists

@app.put("/users/me/preferences")
async def update_preferences(
    preferences: dict,
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user = get_user_from_db(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        user.preferences = preferences
        user.updated_at = datetime.now(UTC)
        db.commit()
        return {"status": "success", "preferences": user.preferences}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
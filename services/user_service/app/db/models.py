from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime, TypeDecorator
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
import json

from .database import Base

class CompatibleArray(TypeDecorator):
    impl = String
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(String)
    
    def process_bind_param(self, value, dialect):
        if dialect.name == 'postgresql':
            return value if value is not None else []
        else:
            return json.dumps(value) if value is not None else "[]"
    
    def process_result_value(self, value, dialect):
        if dialect.name == 'postgresql':
            return value if value is not None else []
        else:
            return json.loads(value) if value is not None else []

class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    preferences = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
    favorite_stores = Column(CompatibleArray(String), default=[])
    shopping_lists = relationship("ShoppingListModel", back_populates="user", cascade="all, delete-orphan")

class ShoppingListModel(Base):
    __tablename__ = "shopping_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String)
    items = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC))
    user = relationship("UserModel", back_populates="shopping_lists")

# Export models
__all__ = ['UserModel', 'ShoppingListModel', 'Base']
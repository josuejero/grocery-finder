# test_main.py

import os

# Set DATABASE_URL to SQLite before importing main.py
os.environ['DATABASE_URL'] = "sqlite:///./test.db"

import asyncio
import logging
import sys
from datetime import datetime, timedelta
import datetime as dt
from typing import Generator

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from main import (
    app,
    Base,
    get_db,
    UserModel,
    ShoppingListModel,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
)

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_user_service.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Use the DATABASE_URL set above
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Create the engine for tests (SQLite)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Ensure foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in SQLALCHEMY_DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def create_test_token(username: str = "testuser") -> str:
    token_data = {
        "sub": username,
        "exp": datetime.now(dt.timezone.utc) + timedelta(minutes=30)
    }
    return jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture
def db() -> Generator:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db) -> Generator:
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    user = UserModel(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        preferences={"theme": "dark"},
        favorite_stores=["store1", "store2"]
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_shopping_list(db, test_user):
    shopping_list = ShoppingListModel(
        user_id=test_user.id,
        name="Test List",
        items=[{"name": "Test Item", "quantity": 1}]
    )
    db.add(shopping_list)
    db.commit()
    db.refresh(shopping_list)
    return shopping_list

def test_health_check(client):
    logger.info("Testing health check endpoint")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["database"] == "connected"

def test_get_user_profile_success(client, test_user):
    logger.info("Testing get user profile endpoint - success case")
    token = create_test_token(test_user.username)
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert data["preferences"] == test_user.preferences
    assert data["favorite_stores"] == test_user.favorite_stores

def test_get_user_profile_invalid_token(client):
    logger.info("Testing get user profile endpoint - invalid token")
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate token"

def test_update_user_profile_success(client, test_user):
    logger.info("Testing update user profile endpoint - success case")
    token = create_test_token(test_user.username)
    update_data = {
        "username": test_user.username,
        "email": "updated@example.com",
        "full_name": "Updated Name",
        "preferences": {"theme": "light"},
        "favorite_stores": ["store3"]
    }
    response = client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == update_data["email"]
    assert data["full_name"] == update_data["full_name"]
    assert data["preferences"] == update_data["preferences"]
    assert data["favorite_stores"] == update_data["favorite_stores"]

def test_create_shopping_list_success(client, test_user):
    logger.info("Testing create shopping list endpoint - success case")
    token = create_test_token(test_user.username)
    shopping_list_data = {
        "name": "New Shopping List",
        "items": [
            {"name": "Item 1", "quantity": 2},
            {"name": "Item 2", "quantity": 1}
        ]
    }
    response = client.post(
        "/users/me/shopping-lists",
        headers={"Authorization": f"Bearer {token}"},
        json=shopping_list_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == shopping_list_data["name"]
    assert data["items"] == shopping_list_data["items"]

def test_get_shopping_lists_success(client, test_user, test_shopping_list):
    logger.info("Testing get shopping lists endpoint - success case")
    token = create_test_token(test_user.username)
    response = client.get(
        "/users/me/shopping-lists",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(lst["name"] == test_shopping_list.name for lst in data)

def test_update_shopping_list_success(client, test_user, test_shopping_list):
    logger.info("Testing update shopping list endpoint - success case")
    token = create_test_token(test_user.username)
    update_data = {
        "name": "Updated List Name",
        "items": [{"name": "Updated Item", "quantity": 3}]
    }
    response = client.put(
        f"/users/me/shopping-lists/{test_shopping_list.id}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["items"] == update_data["items"]

def test_delete_shopping_list_success(client, test_user, test_shopping_list):
    logger.info("Testing delete shopping list endpoint - success case")
    token = create_test_token(test_user.username)
    response = client.delete(
        f"/users/me/shopping-lists/{test_shopping_list.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Shopping list deleted"

def test_update_preferences_success(client, test_user):
    logger.info("Testing update preferences endpoint - success case")
    token = create_test_token(test_user.username)
    new_preferences = {
        "theme": "light",
        "notifications": True,
        "language": "es"
    }
    response = client.put(
        "/users/me/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json=new_preferences
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["preferences"] == new_preferences

def test_nonexistent_shopping_list(client, test_user):
    logger.info("Testing nonexistent shopping list access")
    token = create_test_token(test_user.username)
    response = client.get(
        "/users/me/shopping-lists/99999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Shopping list not found"

def test_unauthorized_access(client):
    logger.info("Testing unauthorized access")
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_expired_token(client):
    logger.info("Testing expired token")
    token_data = {
        "sub": "testuser",
        "exp": datetime.now(dt.timezone.utc) - timedelta(minutes=30)
    }
    expired_token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"

def test_invalid_shopping_list_data(client, test_user):
    logger.info("Testing invalid shopping list data")
    token = create_test_token(test_user.username)
    invalid_data = {
        "items": "not a list"  # Invalid data type
    }
    response = client.post(
        "/users/me/shopping-lists",
        headers={"Authorization": f"Bearer {token}"},
        json=invalid_data
    )
    assert response.status_code == 422

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG"])

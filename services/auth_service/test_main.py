import os
os.environ["MONGODB_URL"] = "mongodb://mongodb:27017"  # Updated for Docker container
os.environ["MONGODB_DATABASE"] = "test_grocery_finder"
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
os.environ["JWT_ALGORITHM"] = "HS256"

import asyncio
import logging
import sys
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from main import app, get_user, create_access_token

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_auth_service.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure max retry attempts and delay for MongoDB connection
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

async def wait_for_mongodb():
    """Helper function to wait for MongoDB to be ready"""
    for attempt in range(MAX_RETRIES):
        try:
            client = AsyncIOMotorClient(os.environ["MONGODB_URL"])
            await client.admin.command('ping')
            client.close()
            logger.info("Successfully connected to MongoDB")
            return
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Failed to connect to MongoDB (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f"Failed to connect to MongoDB after {MAX_RETRIES} attempts")
                raise

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def test_db():
    # Wait for MongoDB to be ready
    await wait_for_mongodb()
    
    # Initialize MongoDB client
    app.mongodb_client = AsyncIOMotorClient(
        os.environ["MONGODB_URL"],
        serverSelectionTimeoutMS=5000  # 5 second timeout
    )
    app.mongodb = app.mongodb_client[os.environ["MONGODB_DATABASE"]]
    
    try:
        await app.mongodb.command("ping")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    
    # Setup test database
    await app.mongodb.command("dropDatabase")
    await setup_test_db()
    
    yield
    
    # Cleanup
    await app.mongodb.command("dropDatabase")
    app.mongodb_client.close()

async def setup_test_db():
    try:
        # Create hashed password for test user
        hashed_password = pwd_context.hash("testpassword123")
        test_user = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": hashed_password,
            "disabled": False
        }
        
        # Create indexes first
        await app.mongodb.users.create_index("username", unique=True)
        await app.mongodb.users.create_index("email", unique=True)
        
        # Insert test user
        result = await app.mongodb.users.insert_one(test_user)
        logger.debug(f"Created test user with ID: {result.inserted_id}")
        logger.debug(f"Test user password hash: {hashed_password}")
        
        # Verify the user was created
        created_user = await app.mongodb.users.find_one({"_id": result.inserted_id})
        if created_user:
            logger.debug("Test user created successfully")
        else:
            logger.error("Failed to create test user")
            raise Exception("Test user creation failed")
            
    except Exception as e:
        logger.error(f"Error setting up test database: {e}")
        raise

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["database"] == "connected"

@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "testpassword123",
            "full_name": "New User"
        }
        response = await ac.post("/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "password" not in data

@pytest.mark.asyncio
async def test_register_duplicate_username():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_data = {
            "username": "testuser",
            "email": "another@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        response = await ac.post("/register", json=user_data)
        assert response.status_code == 400
        assert response.json()["detail"] == "Username already registered"

@pytest.mark.asyncio
async def test_login_success():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        form_data = {
            "username": "testuser",
            "password": "testpassword123",
            "grant_type": "password"
        }
        response = await ac.post("/login", data=form_data)
        logger.debug(f"Login response: {response.status_code} - {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        form_data = {
            "username": "testuser",
            "password": "wrongpassword",
            "grant_type": "password"
        }
        response = await ac.post("/login", data=form_data)
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"

@pytest.mark.asyncio
async def test_get_current_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        access_token = create_access_token({"sub": "testuser"})
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await ac.get("/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        headers = {"Authorization": "Bearer invalid_token"}
        response = await ac.get("/users/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_expired_token():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        expired_token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=-30)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await ac.get("/users/me", headers=headers)
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_user_not_found():
    user = await get_user("nonexistentuser")
    assert user is None

if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG"])
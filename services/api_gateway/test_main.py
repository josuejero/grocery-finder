import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from main import LoginCredentials, app

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_api_gateway.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

app.state.testing = True
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    logger.debug("Setting up mock environment variables")
    try:
        monkeypatch.setenv("JWT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("AUTH_SERVICE_URL", "http://auth:8000")
        monkeypatch.setenv("USER_SERVICE_URL", "http://users:8000")
        monkeypatch.setenv("PRICE_SERVICE_URL", "http://prices:8000")
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "60")
        logger.debug("Mock environment variables set successfully")
    except Exception as e:
        logger.error(f"Failed to set mock environment variables: {str(e)}")
        raise


@pytest.fixture(autouse=True)
def mock_redis():
    logger.debug("Setting up mock Redis client")
    try:
        redis_mock = AsyncMock()
        redis_mock.incr.return_value = 1
        redis_mock.expire.return_value = True

        with patch("main.get_redis_client", return_value=redis_mock):
            logger.debug("Mock Redis client setup complete")
            yield redis_mock
    except Exception as e:
        logger.error(f"Failed to setup mock Redis: {str(e)}")
        raise


def test_health_check():
    logger.debug("Running health check test")
    try:
        response = client.get("/health")
        logger.debug(f"Health check response: {response.json()}")
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "healthy"
        assert "timestamp" in response.json()
        logger.debug("Health check test passed")
    except Exception as e:
        logger.error(f"Health check test failed: {str(e)}")
        raise


def test_login_success():
    logger.debug("Running login success test")
    try:
        test_credentials = LoginCredentials(username="testuser", password="testpass")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            response = client.post("/auth/login", json=test_credentials.model_dump())
            logger.debug(f"Login response: {response.json()}")

            assert response.status_code == 200
            assert "access_token" in response.json()
            logger.debug("Login success test passed")

    except Exception as e:
        logger.error(f"Login success test failed: {str(e)}")
        raise


def test_login_failure():
    logger.debug("Running login failure test")
    try:
        test_credentials = LoginCredentials(username="testuser", password="wrongpass")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid credentials"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            response = client.post("/auth/login", json=test_credentials.model_dump())
            logger.debug(f"Login failure response: {response.json()}")

            assert response.status_code == 401
            assert "detail" in response.json()
            assert response.json()["detail"] == "Invalid credentials"
            logger.debug("Login failure test passed")

    except Exception as e:
        logger.error(f"Login failure test failed: {str(e)}")
        raise


def test_login_service_unavailable():
    logger.debug("Running login service unavailable test")
    try:
        test_credentials = LoginCredentials(username="testuser", password="testpass")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = (
                httpx.RequestError("Connection failed")
            )

            response = client.post("/auth/login", json=test_credentials.model_dump())
            logger.debug(f"Service unavailable response: {response.json()}")

            assert response.status_code == 503
            assert "detail" in response.json()
            assert response.json()["detail"] == "Auth service unavailable"
            logger.debug("Login service unavailable test passed")

    except Exception as e:
        logger.error(f"Login service unavailable test failed: {str(e)}")
        raise


if __name__ == "__main__":
    pytest.main(["-v", "--log-cli-level=DEBUG"])

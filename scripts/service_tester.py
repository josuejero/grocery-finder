import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx
import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cf00a032a7d8943e4e569105b95087b382b31153c3d7aad6138a173da04f89f3")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integration_tests.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ServiceTester:
    def __init__(self):
        self.api_gateway_url = "http://localhost:8000"
        self.auth_service_url = "http://localhost:8001"
        self.user_service_url = "http://localhost:8002"
        self.price_service_url = "http://localhost:8003"
        self.access_token = None
        self.test_user = {
            "username": "testuser123",
            "email": "testuser123@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User"
        }
        self.test_shopping_list = {
            "name": "Test Shopping List",
            "items": [
                {"name": "Milk", "quantity": 1},
                {"name": "Bread", "quantity": 2}
            ]
        }
        self.test_product = {
            "id": "test-product-1",
            "name": "Test Product",
            "category": "Test Category",
            "brand": "Test Brand",
            "description": "Test Description"
        }
        self.test_store = {
            "id": "test-store-1",
            "name": "Test Store",
            "location": "Test Location",
            "address": "123 Test St"
        }
        self.test_price = {
            "store_id": "test-store-1",
            "product_id": "test-product-1",
            "price": 9.99,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
            "unit": "each",
            "quantity": 1
        }

    async def wait_for_services(self, timeout: int = 60):
        logger.info("Waiting for all services to be ready...")
        services = {
            "API Gateway": f"{self.api_gateway_url}/health",
            "Auth Service": f"{self.auth_service_url}/health",
            "User Service": f"{self.user_service_url}/health",
            "Price Service": f"{self.price_service_url}/health"
        }

        start_time = time.time()
        while time.time() - start_time < timeout:
            all_healthy = True
            async with httpx.AsyncClient() as client:
                for service_name, url in services.items():
                    try:
                        response = await client.get(url)
                        if response.status_code != 200:
                            logger.warning(f"{service_name} not ready: {response.status_code}")
                            all_healthy = False
                            break
                        health_data = response.json()
                        if health_data.get("status") != "healthy":
                            logger.warning(f"{service_name} not healthy: {health_data}")
                            all_healthy = False
                            break
                    except Exception as e:
                        logger.warning(f"{service_name} not available: {str(e)}")
                        all_healthy = False
                        break

            if all_healthy:
                logger.info("All services are healthy!")
                return True
            
            await asyncio.sleep(5)

        logger.error("Timeout waiting for services")
        return False

    async def create_test_token(self):
        payload = {
            "sub": self.test_user["username"],
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    async def test_auth_service(self):
        logger.info("\nTesting Auth Service...")
        try:
            async with httpx.AsyncClient() as client:
                logger.info("Testing user registration...")
                response = await client.post(
                    f"{self.auth_service_url}/register",
                    json=self.test_user
                )
                assert response.status_code in [200, 400], f"Registration failed: {response.text}"

                logger.info("Testing user login...")
                response = await client.post(
                    f"{self.auth_service_url}/login",
                    data={
                        "username": self.test_user["username"],
                        "password": self.test_user["password"],
                        "grant_type": "password"
                    }
                )
                assert response.status_code == 200, f"Login failed: {response.text}"
                token_data = response.json()
                self.access_token = token_data["access_token"]

                logger.info("Testing user profile retrieval...")
                response = await client.get(
                    f"{self.auth_service_url}/users/me",
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                assert response.status_code == 200, f"Profile retrieval failed: {response.text}"

                return True
        except Exception as e:
            logger.error(f"Auth service test failed: {str(e)}")
            return False

    async def test_user_service(self):
        logger.info("\nTesting User Service...")
        try:
            if not self.access_token:
                logger.error("No access token available")
                return False

            # Use the token from the successful auth service login
            # This ensures we're using a valid token from a registered user

            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.access_token}"}

                logger.info("Testing user profile endpoints...")
                response = await client.get(
                    f"{self.user_service_url}/users/me",
                    headers=headers
                )
                logger.debug(f"Profile response: {response.status_code} - {response.text}")
                assert response.status_code == 200, f"Profile retrieval failed: {response.text}"

                logger.info("Testing shopping list creation...")
                response = await client.post(
                    f"{self.user_service_url}/users/me/shopping-lists",
                    headers=headers,
                    json=self.test_shopping_list
                )
                logger.debug(f"Shopping list creation response: {response.status_code} - {response.text}")
                assert response.status_code == 200, f"Shopping list creation failed: {response.text}"
                list_id = response.json()["id"]

                logger.info("Testing shopping list retrieval...")
                response = await client.get(
                    f"{self.user_service_url}/users/me/shopping-lists",
                    headers=headers
                )
                assert response.status_code == 200, f"Shopping list retrieval failed: {response.text}"

                logger.info("Testing shopping list update...")
                update_data = {
                    "name": "Updated Shopping List",
                    "items": [{"name": "Eggs", "quantity": 12}]
                }
                response = await client.put(
                    f"{self.user_service_url}/users/me/shopping-lists/{list_id}",
                    headers=headers,
                    json=update_data
                )
                assert response.status_code == 200, f"Shopping list update failed: {response.text}"

                logger.info("Testing shopping list deletion...")
                response = await client.delete(
                    f"{self.user_service_url}/users/me/shopping-lists/{list_id}",
                    headers=headers
                )
                assert response.status_code == 200, f"Shopping list deletion failed: {response.text}"

                return True
        except Exception as e:
            logger.error(f"User service test failed: {str(e)}")
            return False

    async def test_price_service(self):
        logger.info("\nTesting Price Service...")
        try:
            async with httpx.AsyncClient() as client:
                logger.info("Testing price entry creation...")
                response = await client.post(
                    f"{self.price_service_url}/prices",
                    json=self.test_price
                )
                assert response.status_code == 200, f"Price entry creation failed: {response.text}"

                logger.info("Testing price comparison...")
                response = await client.get(
                    f"{self.price_service_url}/prices/compare/{self.test_product['id']}"
                )
                assert response.status_code == 200, f"Price comparison failed: {response.text}"

                logger.info("Testing product search...")
                response = await client.get(
                    f"{self.price_service_url}/products/search",
                    params={"query": "test"}
                )
                assert response.status_code == 200, f"Product search failed: {response.text}"

                return True
        except Exception as e:
            logger.error(f"Price service test failed: {str(e)}")
            return False

    async def run_all_tests(self):
        logger.info("Starting integration tests...")

        if not await self.wait_for_services():
            logger.error("Services are not ready. Aborting tests.")
            return False

        test_results = {
            "Auth Service": await self.test_auth_service(),
            "User Service": await self.test_user_service(),
            "Price Service": await self.test_price_service()
        }

        logger.info("\nTest Results:")
        for service, success in test_results.items():
            status = "✓ Passed" if success else "✗ Failed"
            logger.info(f"{service}: {status}")

        return all(test_results.values())

async def main():
    tester = ServiceTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
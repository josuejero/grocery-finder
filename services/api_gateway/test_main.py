import asyncio
import logging
import os
import sys
import time
import traceback
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import requests
from typing import Optional, Dict, Any

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("docker_api_tests.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "dockertestuser",
    "email": "dockertest@example.com",
    "password": "TestPass123!",
    "full_name": "Docker Test User"
}

class APIGatewayTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.access_token = None
        self.session = requests.Session()

    def wait_for_services(self, max_retries: int = 30, retry_delay: int = 2) -> bool:
        logger.info("Waiting for all services to be ready...")
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    services_status = health_data.get("services", {})
                    
                    all_healthy = all(
                        status == "healthy" 
                        for service, status in services_status.items()
                    )
                    
                    if all_healthy:
                        logger.info("All services are healthy!")
                        return True
                    
                    logger.warning(
                        f"Services status: {', '.join(f'{s}: {st}' for s, st in services_status.items())}"
                    )
                else:
                    logger.warning(f"Health check failed: {response.status_code}")
            except requests.RequestException as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        logger.error("Services failed to become ready")
        return False

    def register_user(self) -> bool:
        logger.info(f"Registering test user: {TEST_USER['username']}")
        try:
            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=TEST_USER,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("User registration successful")
                return True
            elif response.status_code == 400 and "already registered" in response.text:
                logger.info("User already exists")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Registration request failed: {str(e)}")
            return False

    def login(self) -> bool:
        logger.info(f"Logging in as: {TEST_USER['username']}")
        try:
            form_data = {
                "username": TEST_USER["username"],
                "password": TEST_USER["password"]
            }
            
            response = self.session.post(
                f"{self.base_url}/auth/login",
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                self.access_token = response.json()["access_token"]
                logger.info("Login successful")
                return True
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Login request failed: {str(e)}")
            return False

    def test_protected_endpoints(self) -> bool:
        if not self.access_token:
            logger.error("No access token available")
            return False

        endpoints = [
            "/users/me",
            "/users/me/preferences",
            "/users/me/shopping-lists"
        ]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        all_successful = True
        for endpoint in endpoints:
            logger.info(f"Testing endpoint: {endpoint}")
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    headers=headers
                )
                
                if response.status_code in [200, 404]:
                    logger.info(f"Endpoint {endpoint} test passed")
                else:
                    logger.error(
                        f"Endpoint {endpoint} test failed: {response.status_code} - {response.text}"
                    )
                    all_successful = False
            except requests.RequestException as e:
                logger.error(f"Request to {endpoint} failed: {str(e)}")
                all_successful = False

        return all_successful

    def test_rate_limiting(self) -> bool:
        logger.info("Starting rate limit test")
        endpoint = f"{self.base_url}/health"
        requests_to_send = 100

        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=20,
            pool_maxsize=20
        )
        session.mount('http://', adapter)
        
        try:
            logger.debug("Sending warmup request")
            warmup = session.get(endpoint)
            logger.debug(f"Warmup response: {warmup.status_code}")
            
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = []
                for _ in range(requests_to_send):
                    futures.append(executor.submit(session.get, endpoint))
                
                responses = []
                try:
                    for i, future in enumerate(as_completed(futures), 1):
                        try:
                            response = future.result()
                            status_code = response.status_code
                            responses.append(status_code)
                            
                            headers = response.headers
                            rate_limit = headers.get('X-RateLimit-Limit')
                            rate_reset = headers.get('X-RateLimit-Reset')
                            retry_after = headers.get('Retry-After')
                            
                            if status_code == 429:
                                logger.info(f"Rate limit hit after {i} requests")
                                return True
                                
                        except Exception as e:
                            logger.error(f"Error processing request {i}: {str(e)}")
                            
                except Exception as e:
                    logger.error(f"Error in rate limit test: {str(e)}")
                    return False
                    
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error in rate limit test: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        finally:
            session.close()

    def run_all_tests(self) -> bool:
        test_results = {
            "Services Health": self.wait_for_services(),
            "User Registration": self.register_user(),
            "User Login": self.login(),
            "Protected Endpoints": self.test_protected_endpoints(),
            "Rate Limiting": self.test_rate_limiting()
        }

        logger.info("\nTest Results:")
        for test_name, result in test_results.items():
            status = "✓ Passed" if result else "✗ Failed"
            logger.info(f"{test_name}: {status}")

        return all(test_results.values())

def main():
    tester = APIGatewayTester(BASE_URL)
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
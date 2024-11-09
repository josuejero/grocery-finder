import pytest
import requests
import logging
import sys
import time
from typing import Optional, Dict, Any
import socket
import traceback
import urllib.parse
import docker

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





    # In APIGatewayTester class

    async def check_service_health(self, service_url: str, service_name: str) -> bool:
        """Check health of an individual service"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                logger.debug(f"Attempting health check for {service_name} at {service_url}")
                
                # DNS Check
                parsed_url = urllib.parse.urlparse(service_url)
                hostname = parsed_url.hostname
                try:
                    logger.debug(f"Performing DNS lookup for {hostname}")
                    socket.gethostbyname(hostname)
                except socket.gaierror as e:
                    logger.error(f"DNS resolution failed for {hostname}: {e}")
                    return False

                # TCP Connection Check
                port = parsed_url.port or 80
                try:
                    logger.debug(f"Testing TCP connection to {hostname}:{port}")
                    socket.create_connection((hostname, port), timeout=5)
                except (socket.timeout, ConnectionRefusedError) as e:
                    logger.error(f"TCP connection failed to {hostname}:{port}: {e}")
                    return False

                # HTTP Health Check
                try:
                    response = await client.get(f"{service_url}/health")
                    logger.debug(f"Health check response from {service_name}: {response.status_code}")
                    logger.debug(f"Response body: {response.text}")
                    return response.status_code == 200
                except httpx.RequestError as e:
                    logger.error(f"HTTP request failed for {service_name}: {e}")
                    return False
        except Exception as e:
            logger.error(f"Unexpected error checking {service_name} health: {e}")
            logger.error(traceback.format_exc())
            return False

    def wait_for_services(self, max_retries: int = 30, retry_delay: int = 2) -> bool:
        logger.info("Waiting for all services to be ready...")
        
        services = {
            "auth": "http://localhost:8001",
            "user": "http://localhost:8002",
            "price": "http://localhost:8003",
            "redis": "http://localhost:6379",
            "mongodb": "mongodb://localhost:27017",
        }
        
        for attempt in range(max_retries):
            services_status = {}
            try:
                # Check Docker container status first
                logger.debug("Checking Docker container status")
                try:
                    client = docker.from_env()
                    containers = client.containers.list()
                    container_status = {c.name: c.status for c in containers}
                    logger.debug(f"Container status: {container_status}")
                except Exception as e:
                    logger.error(f"Failed to check Docker containers: {e}")

                # Try API Gateway health endpoint
                logger.debug("Attempting API Gateway health check")
                response = self.session.get(
                    f"{self.base_url}/health",
                    timeout=5,
                    headers={"Accept": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.debug(f"API Gateway health response: {response.text}")
                    health_data = response.json()
                    services_status = health_data.get("services", {})
                    
                    # Check network connectivity
                    for service, url in services.items():
                        try:
                            parsed_url = urllib.parse.urlparse(url)
                            sock = socket.create_connection(
                                (parsed_url.hostname, parsed_url.port or 80),
                                timeout=2
                            )
                            sock.close()
                            logger.debug(f"Network connectivity to {service} confirmed")
                        except Exception as e:
                            logger.error(f"Network connectivity check failed for {service}: {e}")
                    
                    all_healthy = all(status == "healthy" for status in services_status.values())
                    if all_healthy:
                        logger.info("All services are healthy!")
                        return True
                    
                    # Detailed service status logging
                    for service, status in services_status.items():
                        if status != "healthy":
                            logger.warning(f"Service {service} status: {status}")
                            
                    logger.warning(
                        f"Services status: {', '.join(f'{s}: {st}' for s, st in services_status.items())}"
                    )
                else:
                    logger.warning(
                        f"Health check failed: {response.status_code}\n"
                        f"Response headers: {dict(response.headers)}\n"
                        f"Response body: {response.text}"
                    )
            except requests.RequestException as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                logger.debug(f"Exception details: {traceback.format_exc()}")
                
                # Try to get more network diagnostic information
                try:
                    logger.debug(f"Running network diagnostics for {self.base_url}")
                    parsed_url = urllib.parse.urlparse(self.base_url)
                    hostname = parsed_url.hostname
                    
                    # Check if hostname resolves
                    try:
                        ip = socket.gethostbyname(hostname)
                        logger.debug(f"DNS resolution: {hostname} -> {ip}")
                    except socket.gaierror as e:
                        logger.error(f"DNS resolution failed: {e}")
                    
                    # Try traceroute
                    if os.name != "nt":  # Not on Windows
                        try:
                            traceroute = subprocess.check_output(
                                ["traceroute", hostname],
                                stderr=subprocess.STDOUT,
                                timeout=10
                            ).decode()
                            logger.debug(f"Traceroute results:\n{traceroute}")
                        except Exception as e:
                            logger.error(f"Traceroute failed: {e}")
                except Exception as e:
                    logger.error(f"Network diagnostics failed: {e}")
            
            if attempt < max_retries - 1:
                logger.debug(f"Waiting {retry_delay} seconds before next attempt")
                time.sleep(retry_delay)
        
        logger.error("Services failed to become ready")
        return False




    def register_user(self) -> bool:
        logger.info(f"Registering test user: {TEST_USER['username']}")
        try:
            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=TEST_USER
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
                "password": TEST_USER["password"],
                "grant_type": "password"
            }
            
            response = self.session.post(
                f"{self.base_url}/auth/login",
                data=form_data
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

        headers = {"Authorization": f"Bearer {self.access_token}"}
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
                    logger.error(f"Endpoint {endpoint} test failed: {response.status_code} - {response.text}")
                    all_successful = False
            except requests.RequestException as e:
                logger.error(f"Request to {endpoint} failed: {str(e)}")
                all_successful = False

        return all_successful

    def run_all_tests(self) -> bool:
        test_results = {
            "Services Health": self.wait_for_services(),
            "User Registration": self.register_user(),
            "User Login": self.login(),
            "Protected Endpoints": self.test_protected_endpoints()
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
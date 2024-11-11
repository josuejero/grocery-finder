import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
import datetime as dt
from typing import Dict, Optional, List, Any
import httpx
import jwt
from dotenv import load_dotenv
from datetime import UTC
import statistics
import traceback
from dataclasses import dataclass
from enum import Enum
import concurrent.futures
from functools import wraps
import jsonschema

# Load environment variables
load_dotenv()

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler("integration_tests.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    PASSED = "✓ Passed"
    FAILED = "✗ Failed"
    SKIPPED = "○ Skipped"

@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float
    error: Optional[str] = None
    response_data: Optional[Dict] = None
    assertions_passed: int = 0
    assertions_failed: int = 0

@dataclass
class TestSuite:
    name: str
    results: List[TestResult]
    start_time: datetime
    end_time: Optional[datetime] = None
    setup_duration: Optional[float] = None
    cleanup_duration: Optional[float] = None

def async_test(cleanup: bool = True):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            test_name = func.__name__
            try:
                if cleanup:
                    await self.cleanup_test_data(test_name)
                result = await func(self, *args, **kwargs)
                duration = time.time() - start_time
                return TestResult(
                    name=test_name,
                    status=TestStatus.PASSED,
                    duration=duration,
                    response_data=result if isinstance(result, dict) else None
                )
            except AssertionError as e:
                duration = time.time() - start_time
                logger.error(f"Test {test_name} failed: {str(e)}")
                logger.error(traceback.format_exc())
                return TestResult(
                    name=test_name,
                    status=TestStatus.FAILED,
                    duration=duration,
                    error=str(e)
                )
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Test {test_name} failed with unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                return TestResult(
                    name=test_name,
                    status=TestStatus.FAILED,
                    duration=duration,
                    error=f"Unexpected error: {str(e)}"
                )
        return wrapper
    return decorator

# Response schemas for validation
SCHEMAS = {
    "auth_register": {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "full_name": {"type": "string"}
        },
        "required": ["username", "email"]
    },
    "auth_login": {
        "type": "object",
        "properties": {
            "access_token": {"type": "string"},
            "token_type": {"type": "string"}
        },
        "required": ["access_token", "token_type"]
    },
    "shopping_list": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "integer"}
                    },
                    "required": ["name", "quantity"]
                }
            }
        },
        "required": ["id", "name", "items"]
    }
}

class ServiceTester:
    def __init__(self):
        self.api_gateway_url = "http://localhost:8000"
        self.auth_service_url = "http://localhost:8001"
        self.user_service_url = "http://localhost:8002"
        self.price_service_url = "http://localhost:8003"
        self.access_token = None
        self.test_suites: List[TestSuite] = []
        self.current_suite: Optional[TestSuite] = None
        self.response_times: Dict[str, List[float]] = {}
        
        # Generate unique test data for each run
        self.test_id = str(uuid.uuid4())[:8]
        self.test_user = {
            "username": f"testuser_{self.test_id}",
            "email": f"testuser_{self.test_id}@example.com",
            "password": "TestPassword123!",
            "full_name": f"Test User {self.test_id}"
        }
        self.test_shopping_list = {
            "name": f"Test Shopping List {self.test_id}",
            "items": [
                {"name": "Milk", "quantity": 1},
                {"name": "Bread", "quantity": 2}
            ]
        }
        self.test_product = {
            "id": f"test-product-{self.test_id}",
            "name": "Test Product",
            "category": "Test Category",
            "brand": "Test Brand",
            "description": "Test Description"
        }
        
        self.test_price = {
            "store_id": f"test-store-{self.test_id}",
            "product_id": f"test-product-{self.test_id}",
            "price": 9.99,
            "currency": "USD",
            "timestamp": datetime.now(UTC).isoformat(),
            "unit": "each",
            "quantity": 1
        }
        self.sync_user_url = f"{self.user_service_url}/users/sync"
        self.created_resources = []

    async def cleanup_test_data(self, test_name: str):
        """Clean up any test data created during the test"""
        if test_name in self.created_resources:
            logger.info(f"Cleaning up test data for {test_name}")
            try:
                if "shopping_list" in test_name:
                    # Delete test shopping lists
                    headers = {"Authorization": f"Bearer {self.access_token}"}
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{self.user_service_url}/users/me/shopping-lists",
                            headers=headers
                        )
                        lists = response.json()
                        for lst in lists:
                            if lst["name"].startswith("Test Shopping List"):
                                await client.delete(
                                    f"{self.user_service_url}/users/me/shopping-lists/{lst['id']}",
                                    headers=headers
                                )
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    async def validate_response(self, response_data: Dict, schema_name: str) -> bool:
        """Validate response data against schema"""
        try:
            jsonschema.validate(instance=response_data, schema=SCHEMAS[schema_name])
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Response validation failed for {schema_name}: {e}")
            return False

    async def start_test_suite(self, name: str):
        """Start a new test suite"""
        self.current_suite = TestSuite(
            name=name,
            results=[],
            start_time=datetime.now(UTC)
        )
        logger.info(f"\nStarting test suite: {name}")

    async def end_test_suite(self):
        """End the current test suite and store results"""
        if self.current_suite:
            self.current_suite.end_time = datetime.now(UTC)
            self.test_suites.append(self.current_suite)
            await self.print_suite_results(self.current_suite)

    async def print_suite_results(self, suite: TestSuite):
        """Print detailed results for a test suite"""
        duration = (suite.end_time - suite.start_time).total_seconds()
        passed = sum(1 for r in suite.results if r.status == TestStatus.PASSED)
        total = len(suite.results)
        
        logger.info(f"\nTest Suite: {suite.name}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Results: {passed}/{total} passed")
        
        for result in suite.results:
            status_symbol = "✓" if result.status == TestStatus.PASSED else "✗"
            logger.info(f"\n{status_symbol} {result.name} ({result.duration:.2f}s)")
            if result.error:
                logger.error(f"  Error: {result.error}")
            if result.response_data:
                logger.info(f"  Response: {json.dumps(result.response_data, indent=2)}")

    def record_response_time(self, endpoint: str, duration: float):
        """Record response time for metrics"""
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []
        self.response_times[endpoint].append(duration)

    async def print_performance_metrics(self):
        """Print performance metrics for all recorded response times"""
        logger.info("\nPerformance Metrics:")
        for endpoint, times in self.response_times.items():
            if times:
                avg_time = statistics.mean(times)
                max_time = max(times)
                min_time = min(times)
                p95_time = sorted(times)[int(len(times) * 0.95)]
                logger.info(f"\n{endpoint}:")
                logger.info(f"  Average: {avg_time:.3f}s")
                logger.info(f"  95th percentile: {p95_time:.3f}s")
                logger.info(f"  Min: {min_time:.3f}s")
                logger.info(f"  Max: {max_time:.3f}s")




    @async_test()
    async def test_auth_service_register(self):
        """Test user registration"""
        response_data = None
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.post(
                f"{self.auth_service_url}/register",
                json=self.test_user
            )
            duration = time.time() - start_time
            self.record_response_time("auth_register", duration)
            
            assert response.status_code in [200, 400], \
                f"Registration failed: {response.text}"
            
            if response.status_code == 200:
                # First get a token
                login_response = await client.post(
                    f"{self.auth_service_url}/login",
                    data={
                        "username": self.test_user["username"],
                        "password": self.test_user["password"],
                        "grant_type": "password"
                    }
                )
                assert login_response.status_code == 200
                token = login_response.json()["access_token"]
                
                # Then sync user
                sync_response = await client.post(
                    f"{self.user_service_url}/users/sync",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"username": self.test_user["username"]}
                )
                assert sync_response.status_code == 200, \
                    f"User sync failed: {sync_response.text}"
                
                response_data = response.json()
                
            return response_data





    @async_test()
    async def test_auth_service_login(self):
        """Test user login"""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.post(
                f"{self.auth_service_url}/login",
                data={
                    "username": self.test_user["username"],
                    "password": self.test_user["password"],
                    "grant_type": "password"
                }
            )
            duration = time.time() - start_time
            self.record_response_time("auth_login", duration)
            
            assert response.status_code == 200, \
                f"Login failed: {response.text}"
            
            data = response.json()
            assert await self.validate_response(data, "auth_login"), \
                "Response validation failed"
                
            self.access_token = data["access_token"]
            return data

    # Add more test methods...
    
    # Add these methods to the ServiceTester class:

    @async_test()
    async def test_create_shopping_list(self):
        """Test creating a new shopping list"""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.post(
                f"{self.user_service_url}/users/me/shopping-lists",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=self.test_shopping_list
            )
            duration = time.time() - start_time
            self.record_response_time("create_shopping_list", duration)
            
            assert response.status_code == 200, \
                f"Shopping list creation failed: {response.text}"
            
            data = response.json()
            assert await self.validate_response(data, "shopping_list"), \
                "Response validation failed"
            
            self.created_resources.append(("shopping_list", data["id"]))
            return data




    @async_test()
    async def test_get_shopping_lists(self):
        """Test retrieving all shopping lists"""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.get(
                f"{self.user_service_url}/users/me/shopping-lists",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            duration = time.time() - start_time
            self.record_response_time("get_shopping_lists", duration)
            
            assert response.status_code == 200, \
                f"Shopping list retrieval failed: {response.text}"
            
            data = response.json()
            return {"status": "success", "data": data}







    @async_test()
    async def test_update_shopping_list(self):
        """Test updating a shopping list"""
        lists_result = await self.test_get_shopping_lists()
        if not lists_result.get("data"):
            return {"status": "skipped", "reason": "No shopping lists to update"}
        
        lists = lists_result["data"]
        if not lists:
            return {"status": "skipped", "reason": "No shopping lists to update"}
        
        list_id = lists[0]["id"]
        updated_list = {
            "name": f"Updated List {self.test_id}",
            "items": [{"name": "Updated Item", "quantity": 3}]
        }
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.put(
                f"{self.user_service_url}/users/me/shopping-lists/{list_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=updated_list
            )
            duration = time.time() - start_time
            self.record_response_time("update_shopping_list", duration)
            
            assert response.status_code == 200, \
                f"Shopping list update failed: {response.text}"
            
            return {"status": "success", "data": response.json()}

    @async_test()
    async def test_delete_shopping_list(self):
        """Test deleting a shopping list"""
        lists_result = await self.test_get_shopping_lists()
        if not lists_result.get("data"):
            return {"status": "skipped", "reason": "No shopping lists to delete"}
        
        lists = lists_result["data"]
        if not lists:
            return {"status": "skipped", "reason": "No shopping lists to delete"}
        
        list_id = lists[0]["id"]
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.delete(
                f"{self.user_service_url}/users/me/shopping-lists/{list_id}",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            duration = time.time() - start_time
            self.record_response_time("delete_shopping_list", duration)
            
            assert response.status_code == 200, \
                f"Shopping list deletion failed: {response.text}"
            
            return {"status": "success", "deleted_id": list_id}






    @async_test()
    async def test_price_entry_creation(self):
        """Test creating a new price entry"""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.post(
                f"{self.price_service_url}/prices",
                json=self.test_price
            )
            duration = time.time() - start_time
            self.record_response_time("create_price", duration)
            
            assert response.status_code == 200, \
                f"Price entry creation failed: {response.text}"
            
            data = response.json()
            assert data["price"] == self.test_price["price"], \
                "Price value mismatch"
            
            return data

    @async_test()
    async def test_price_comparison(self):
        """Test price comparison functionality"""
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            response = await client.get(
                f"{self.price_service_url}/prices/compare/{self.test_product['id']}"
            )
            duration = time.time() - start_time
            self.record_response_time("price_comparison", duration)
            
            assert response.status_code == 200, \
                f"Price comparison failed: {response.text}"
            
            data = response.json()
            assert "product_id" in data, "Missing product_id in response"
            assert "price_comparison" in data, "Missing price comparison data"
            
            return data

    async def run_all_tests(self):
        """Run all test suites"""
        logger.info("Starting integration tests...")
        
        try:
            # Authentication Suite
            await self.start_test_suite("Authentication Tests")
            auth_results = [
                await self.test_auth_service_register(),
                await self.test_auth_service_login()
            ]
            self.current_suite.results.extend(auth_results)
            await self.end_test_suite()
            
            # Shopping Lists Suite
            await self.start_test_suite("Shopping Lists Tests")
            if self.access_token:
                shopping_results = [
                    await self.test_create_shopping_list(),
                    await self.test_get_shopping_lists(),
                    await self.test_update_shopping_list(),
                    await self.test_delete_shopping_list()
                ]
                self.current_suite.results.extend(shopping_results)
            else:
                logger.error("Skipping shopping list tests - no access token")
            await self.end_test_suite()
            
            # Price Service Suite
            await self.start_test_suite("Price Service Tests")
            price_results = [
                await self.test_price_entry_creation(),
                await self.test_price_comparison()
            ]
            self.current_suite.results.extend(price_results)
            await self.end_test_suite()
            
            # Print overall metrics
            await self.print_performance_metrics()
            
            # Calculate overall success
            total_tests = sum(len(suite.results) for suite in self.test_suites)
            passed_tests = sum(
                sum(1 for r in suite.results if r.status == TestStatus.PASSED)
                for suite in self.test_suites
            )
            
            logger.info(f"\nOverall Results: {passed_tests}/{total_tests} tests passed")
            
            return passed_tests == total_tests
            
        except Exception as e:
            logger.error(f"Error during test execution: {e}")
            logger.error(traceback.format_exc())
            return False





async def main():
    tester = ServiceTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
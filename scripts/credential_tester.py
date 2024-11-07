import asyncio
import logging
import os
import socket
import dns.resolver
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
import jwt
import motor.motor_asyncio
import psycopg2
import redis
from dotenv import dotenv_values

logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler("credential_tests.log"),
                            logging.StreamHandler()])

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
    "MONGODB_URL", "MONGODB_DATABASE",
    "AUTH_SERVICE_URL", "USER_SERVICE_URL", "PRICE_SERVICE_URL",
    "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
    "RATE_LIMIT_PER_MINUTE", "LOG_LEVEL", "BCRYPT_SALT_ROUNDS"
]

def load_env_vars():
    env_path = Path(".env")
    if not env_path.exists():
        logger.error("No .env file found")
        return False
    config = dotenv_values(env_path)
    os.environ.update(config)
    return all(var in os.environ for var in REQUIRED_ENV_VARS)

async def check_dns_records(hostname):
    try:
        logger.debug(f"Checking DNS A records for {hostname}")
        a_records = dns.resolver.resolve(hostname, 'A')
        logger.debug(f"Found A records: {[str(r) for r in a_records]}")
        return True
    except dns.resolver.NXDOMAIN:
        logger.error(f"No DNS records found for {hostname}")
        return False
    except dns.resolver.NoAnswer:
        logger.error(f"No A records found for {hostname}")
        return False
    except Exception as e:
        logger.error(f"DNS lookup error for {hostname}: {str(e)}")
        return False

async def test_tcp_connection(hostname, port):
    try:
        logger.debug(f"Attempting TCP connection to {hostname}:{port}")
        sock = socket.create_connection((hostname, port), timeout=5)
        sock.close()
        logger.debug(f"Successfully connected to {hostname}:{port}")
        return True
    except socket.timeout:
        logger.error(f"Connection timeout to {hostname}:{port}")
        return False
    except ConnectionRefusedError:
        logger.error(f"Connection refused by {hostname}:{port}")
        return False
    except Exception as e:
        logger.error(f"TCP connection error to {hostname}:{port}: {str(e)}")
        return False

async def test_http_endpoint(url):
    try:
        logger.debug(f"Testing HTTP endpoint: {url}")
        response = requests.get(url, timeout=5)
        logger.debug(f"HTTP response status: {response.status_code}")
        return response.status_code < 500
    except requests.exceptions.ConnectionError:
        logger.error(f"Failed to connect to HTTP endpoint: {url}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"HTTP request timeout for: {url}")
        return False
    except Exception as e:
        logger.error(f"HTTP request error for {url}: {str(e)}")
        return False

async def test_service_url(service_name, url):
    logger.info(f"\nTesting {service_name} URL: {url}")
    
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        logger.debug(f"Parsed URL components for {service_name}:")
        logger.debug(f"  Scheme: {parsed_url.scheme}")
        logger.debug(f"  Hostname: {hostname}")
        logger.debug(f"  Port: {port}")
        logger.debug(f"  Path: {parsed_url.path}")
        
        try:
            ip_addresses = socket.gethostbyname_ex(hostname)
            logger.debug(f"DNS Resolution results for {hostname}:")
            logger.debug(f"  Canonical name: {ip_addresses[0]}")
            logger.debug(f"  IP Addresses: {ip_addresses[2]}")
        except socket.gaierror as e:
            logger.error(f"DNS resolution failed for {hostname}")
            logger.error(f"Error details: {str(e)}")
            
            dns_check = await check_dns_records(hostname)
            if not dns_check:
                logger.error(f"No DNS records found for {hostname}")
                return False
            
        connection_result = await test_tcp_connection(hostname, port)
        if not connection_result:
            return False
            
        if parsed_url.scheme in ['http', 'https']:
            endpoint_result = await test_http_endpoint(url)
            if not endpoint_result:
                return False
                
        logger.info(f"{service_name} URL verification successful")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error testing {service_name} URL: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_jwt_token():
    try:
        token_data = {
            "sub": "test_user",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        token = jwt.encode(
            token_data,
            os.getenv("JWT_SECRET_KEY"),
            algorithm=os.getenv("JWT_ALGORITHM")
        )
        jwt.decode(token, os.getenv("JWT_SECRET_KEY"), 
                  algorithms=[os.getenv("JWT_ALGORITHM")])
        return True
    except Exception as e:
        logger.error(f"JWT Token Test Failed: {str(e)}")
        return False

async def test_postgres_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            database=os.getenv("POSTGRES_DB")
        )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"PostgreSQL Test Failed: {str(e)}")
        return False

async def test_mongodb_connection():
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
        await client.admin.command('ping')
        client.close()
        return True
    except Exception as e:
        logger.error(f"MongoDB Test Failed: {str(e)}")
        return False

async def test_redis_connection():
    try:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )
        redis_client.ping()
        redis_client.close()
        return True
    except Exception as e:
        logger.error(f"Redis Test Failed: {str(e)}")
        return False

async def main():
    if not load_env_vars():
        logger.error("Missing required environment variables")
        return

    results = {
        "JWT Token": await test_jwt_token(),
        "PostgreSQL": await test_postgres_connection(),
        "MongoDB": await test_mongodb_connection(),
        "Redis": await test_redis_connection()
    }

    print("\nTest Results:")
    for service, success in results.items():
        status = "✓ Passed" if success else "✗ Failed"
        print(f"{service}: {status}")

    if not all(results.values()):
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
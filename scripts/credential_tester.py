import asyncio
import logging
import os
import socket
import dns.resolver
from datetime import datetime, timedelta, UTC
from pathlib import Path
from urllib.parse import urlparse
import boto3
import jwt
import motor.motor_asyncio
import psycopg2
import redis
import requests
from dotenv import dotenv_values
import aioboto3

logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler("credential_tests.log"),
                            logging.StreamHandler()])

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
    "JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
    "MONGODB_URL", "MONGODB_DATABASE",
    "COGNITO_USER_POOL_ID", "COGNITO_APP_CLIENT_ID", "COGNITO_AWS_REGION",
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

async def test_aws_credentials():
    try:
        session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        sts = session.client('sts')
        sts.get_caller_identity()
        return True
    except Exception as e:
        logger.error(f"AWS Credentials Test Failed: {str(e)}")
        return False

async def test_cognito_credentials():
    try:
        async with aioboto3.Session().client(
            'cognito-idp',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("COGNITO_AWS_REGION")
        ) as cognito:
            await cognito.describe_user_pool(
                UserPoolId=os.getenv("COGNITO_USER_POOL_ID")
            )
            await cognito.describe_user_pool_client(
                UserPoolId=os.getenv("COGNITO_USER_POOL_ID"),
                ClientId=os.getenv("COGNITO_APP_CLIENT_ID")
            )
        return True
    except Exception as e:
        logger.error(f"Cognito Credentials Test Failed: {str(e)}")
        return False

async def test_jwt_token():
    try:
        token_data = {
            "sub": "test_user",
            "exp": datetime.now(UTC) + timedelta(minutes=30)
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
        redis_host = os.getenv("REDIS_HOST", "")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_password = os.getenv("REDIS_PASSWORD", "")

        logger.debug(f"Redis cluster connection attempt:")
        logger.debug(f"Configuration Endpoint: {redis_host}")
        logger.debug(f"Port: {redis_port}")
        logger.debug(f"Password length: {len(redis_password) if redis_password else 0}")
        logger.debug(f"SSL: enabled")

        # Clean up the host
        if ":" in redis_host:
            redis_host = redis_host.split(":")[0]
            logger.debug(f"Cleaned host: {redis_host}")

        # Setup connection options
        connection_kwargs = {
            "host": redis_host,
            "port": int(redis_port),
            "password": redis_password,
            "ssl": True,
            "ssl_cert_reqs": None,
            "decode_responses": True,
            "socket_connect_timeout": 5.0,
            "socket_timeout": 5.0,
            "retry_on_timeout": True,
        }

        # First try direct non-cluster connection
        try:
            logger.debug("Attempting direct Redis connection first...")
            redis_client = redis.Redis(**connection_kwargs)
            ping_result = redis_client.ping()
            logger.debug(f"Direct connection ping result: {ping_result}")
            redis_client.close()
            logger.info("Direct Redis connection successful")
            return True
        except Exception as direct_error:
            logger.debug(f"Direct connection failed: {str(direct_error)}")
            logger.debug("Falling back to cluster connection...")

        # Try cluster connection
        try:
            logger.debug("Creating Redis Cluster connection...")
            
            # Create nodes list
            startup_node = redis.cluster.ClusterNode(
                host=redis_host,
                port=int(redis_port)
            )
            
            redis_client = redis.cluster.RedisCluster(
                startup_nodes=[startup_node],
                cluster_error_retry_attempts=3,
                password=redis_password,
                decode_responses=True,
                skip_full_coverage_check=True,
                ssl=True,
                ssl_cert_reqs=None,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True
            )

            logger.debug("Testing cluster connection...")
            
            # Test basic operations
            test_key = "cluster_test"
            logger.debug("Testing SET operation...")
            redis_client.set(test_key, "1", ex=5)
            
            logger.debug("Testing GET operation...")
            value = redis_client.get(test_key)
            logger.debug(f"Retrieved value: {value}")
            
            logger.debug("Testing DELETE operation...")
            redis_client.delete(test_key)
            
            redis_client.close()
            logger.info("Redis cluster connection test successful")
            return True

        except Exception as cluster_error:
            logger.error(f"Redis cluster connection failed: {str(cluster_error)}")
            if hasattr(cluster_error, 'args') and cluster_error.args:
                logger.error(f"Detailed error: {cluster_error.args[0]}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error testing Redis: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        try:
            if 'redis_client' in locals():
                redis_client.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")

async def main():
    if not load_env_vars():
        logger.error("Missing required environment variables")
        return

    results = {
        "AWS Credentials": await test_aws_credentials(),
        "Cognito Credentials": await test_cognito_credentials(),
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
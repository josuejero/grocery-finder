import asyncio
import logging
import os
import socket
import sys
import dns.resolver
from datetime import datetime, timedelta, UTC
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import boto3
from jose import jwt
import motor.motor_asyncio
import psycopg2
from dotenv import dotenv_values
import pymongo.errors

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("credential_tests.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

ENV_VARS = [
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "MONGODB_URL",
    "MONGODB_DATABASE",
    "COGNITO_USER_POOL_ID",
    "COGNITO_APP_CLIENT_ID",
    "COGNITO_AWS_REGION"
]

for key in ENV_VARS:
    if key in os.environ:
        del os.environ[key]

script_dir = Path(__file__).parent
project_root = script_dir.parent
env_path = project_root / ".env"

if not env_path.exists():
    logger.error(f"No .env file found at {env_path}")
    sys.exit(1)

logger.debug(f"Loading .env from: {env_path}")
config = dotenv_values(env_path)
os.environ.update(config)

async def test_aws_credentials():
    logger.info("Testing AWS Credentials")
    try:
        session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        
        logger.info(f"AWS Authentication Successful - Account ID: {identity['Account']}")
        return True
    except Exception as e:
        logger.error(f"AWS Credentials Test Failed: {str(e)}")
        return False

async def test_cognito_configuration():
    logger.info("Testing Cognito Configuration")
    try:
        cognito_idp = boto3.client('cognito-idp', 
            region_name=os.getenv("COGNITO_AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        
        user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
        client_id = os.getenv("COGNITO_APP_CLIENT_ID")
        
        if not user_pool_id or not client_id:
            logger.error("Cognito configuration missing")
            if not user_pool_id:
                logger.error("COGNITO_USER_POOL_ID is not set")
            if not client_id:
                logger.error("COGNITO_APP_CLIENT_ID is not set")
            return False
            
        response = cognito_idp.describe_user_pool(
            UserPoolId=user_pool_id
        )
        
        logger.debug(f"User Pool Name: {response['UserPool']['Name']}")
        
        app_client = cognito_idp.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id
        )
        
        logger.debug(f"App Client Name: {app_client['UserPoolClient']['ClientName']}")
        logger.info("Cognito Configuration Test Successful")
        return True
        
    except cognito_idp.exceptions.ResourceNotFoundException as e:
        logger.error(f"Cognito Resource Not Found: {str(e)}")
        logger.error("Check if your User Pool ID and Client ID are correct")
        return False
    except cognito_idp.exceptions.InvalidParameterException as e:
        logger.error(f"Cognito Invalid Parameter: {str(e)}")
        logger.error("Check if your User Pool ID format is correct")
        return False
    except Exception as e:
        logger.error(f"Cognito Configuration Test Failed: {str(e)}")
        return False

async def test_jwt_token():
    logger.info("Testing JWT Token Generation")
    try:
        token_data = {
            "sub": "test_user",
            "exp": datetime.now(UTC) + timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES")))
        }
        
        token = jwt.encode(
            token_data,
            os.getenv("JWT_SECRET_KEY"),
            algorithm=os.getenv("JWT_ALGORITHM")
        )
        
        decoded = jwt.decode(
            token,
            os.getenv("JWT_SECRET_KEY"),
            algorithms=[os.getenv("JWT_ALGORITHM")]
        )
        
        logger.info("JWT Token Test Successful")
        return True
    except Exception as e:
        logger.error(f"JWT Token Test Failed: {str(e)}")
        return False

async def test_dns_resolution(host):
    logger.debug(f"Testing DNS resolution for {host}")
    try:
        ip_addresses = socket.getaddrinfo(host, None)
        logger.debug(f"Standard DNS resolution results for {host}: {ip_addresses}")
        
        try:
            srv_records = dns.resolver.resolve(f"_mongodb._tcp.{host}", "SRV")
            logger.debug(f"SRV records for {host}:")
            for srv in srv_records:
                logger.debug(f"  Priority: {srv.priority}, Weight: {srv.weight}, Port: {srv.port}, Target: {srv.target}")
        except Exception as e:
            logger.debug(f"No SRV records found for {host}: {str(e)}")
            
        return True
    except Exception as e:
        logger.error(f"DNS resolution failed for {host}: {str(e)}")
        return False

def check_network_connectivity(host, port, service_name=""):
    logger.debug(f"Checking network connectivity to {host}:{port} {service_name}")
    
    try:
        logger.debug(f"Resolving hostname: {host}")
        ip_address = socket.gethostbyname(host)
        logger.debug(f"Resolved {host} to {ip_address}")
        
        try:
            resolver = dns.resolver.Resolver()
            records = resolver.resolve(host, 'A')
            logger.debug(f"DNS A records for {host}:")
            for record in records:
                logger.debug(f"  {record}")
        except Exception as e:
            logger.debug(f"DNS lookup failed for {host}: {str(e)}")
            
        logger.debug(f"Attempting TCP connection to {host}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip_address, int(port)))
        
        if result == 0:
            logger.debug(f"Successfully connected to {host}:{port}")
            return True
        else:
            logger.error(f"Failed to connect to {host}:{port} (Error code: {result})")
            return False
            
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed for {host}: {str(e)}")
        return False
    except socket.timeout as e:
        logger.error(f"Connection timeout to {host}:{port}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Network connectivity check failed: {type(e).__name__}: {str(e)}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass
        
        
async def test_postgres_connection():
    logger.info("Testing PostgreSQL Connection")
    
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    
    # Log connection details (safely)
    logger.debug(f"PostgreSQL connection parameters:")
    logger.debug(f"  Host: {host}")
    logger.debug(f"  Port: {port}")
    logger.debug(f"  Database: {db}")
    logger.debug(f"  User: {user}")
    
    # Check network connectivity
    if not check_network_connectivity(host, int(port), "PostgreSQL"):
        logger.error("Network connectivity check failed")
        return False
    
    try:
        logger.debug("Attempting PostgreSQL connection...")
        conn_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": db,
            "connect_timeout": 5,
            "keepalives": 1,
            "keepalives_idle": 5,
            "keepalives_interval": 2,
            "keepalives_count": 2,
            "sslmode": "require"
        }
        
        conn = psycopg2.connect(**conn_params)
        logger.debug("Connection established, checking server version...")
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.info(f"PostgreSQL Connection Successful - Version: {version[0]}")
        
        # Test basic database operations
        logger.debug("Testing basic database operations...")
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        logger.debug(f"Connected to database '{db_info[0]}' as user '{db_info[1]}'")
        
        cursor.close()
        conn.close()
        logger.debug("PostgreSQL connection test completed successfully")
        return True
        
    except psycopg2.OperationalError as e:
        logger.error(f"PostgreSQL Operational Error: {str(e)}")
        if "password authentication failed" in str(e).lower():
            logger.error("Authentication failed. Check credentials.")
        elif "connection refused" in str(e).lower():
            logger.error("Connection refused. Check if server is running and accessible.")
        elif "timeout expired" in str(e).lower():
            logger.error("Connection timeout. Check network and firewall settings.")
        elif "no pg_hba.conf entry" in str(e).lower():
            logger.error("Access denied. Check server's pg_hba.conf configuration.")
        return False
        
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL Error: {e.diag.message_primary if hasattr(e, 'diag') else str(e)}")
        logger.error(f"Error Code: {e.pgcode if hasattr(e, 'pgcode') else 'Unknown'}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error in PostgreSQL connection: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
async def test_mongodb_connection():
    logger.info("Testing MongoDB Connection")
    
    mongodb_url = os.getenv("MONGODB_URL")
    mongodb_db = os.getenv("MONGODB_DATABASE")
    
    if not mongodb_url or not mongodb_db:
        logger.error("MongoDB configuration missing")
        if not mongodb_url:
            logger.error("MONGODB_URL is not set")
        if not mongodb_db:
            logger.error("MONGODB_DATABASE is not set")
        return False
    
    client = None
    try:
        # Parse and validate MongoDB URL
        logger.debug("Parsing MongoDB URL...")
        parsed_url = urlparse(mongodb_url)
        
        # Log URL components (without credentials)
        safe_url = mongodb_url.replace(parsed_url.password or "", "****") if parsed_url.password else mongodb_url
        logger.debug(f"MongoDB URL components:")
        logger.debug(f"  Scheme: {parsed_url.scheme}")
        logger.debug(f"  Hostname: {parsed_url.hostname}")
        logger.debug(f"  Port: {parsed_url.port or 'default'}")
        logger.debug(f"  Username: {parsed_url.username or 'none'}")
        logger.debug(f"  Database: {mongodb_db}")
        logger.debug(f"  Full URL (sanitized): {safe_url}")
        
        # Validate URL scheme
        if parsed_url.scheme not in ['mongodb', 'mongodb+srv']:
            logger.error(f"Invalid MongoDB URL scheme: {parsed_url.scheme}")
            return False
            
        # Test DNS resolution and connectivity
        if parsed_url.scheme == 'mongodb+srv':
            logger.debug("Using mongodb+srv protocol, skipping direct connection test")
        else:
            host = parsed_url.hostname
            port = parsed_url.port or 27017
            if not check_network_connectivity(host, port, "MongoDB"):
                return False
        
        # Attempt connection
        logger.debug("Initializing MongoDB client...")
        client = motor.motor_asyncio.AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        
        # Test connection
        logger.debug("Testing MongoDB connection...")
        db = client[mongodb_db]
        
        logger.debug("Executing ping command...")
        await db.command("ping")
        
        logger.debug("Fetching server information...")
        server_info = await db.command("serverStatus")
        
        version = server_info.get('version', 'unknown')
        logger.info(f"MongoDB Connection Successful - Version: {version}")
        
        # Test database access
        logger.debug("Testing database access...")
        collections = await db.list_collection_names()
        logger.debug(f"Available collections: {collections}")
        
        return True
        
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB Server Selection Timeout: {str(e)}")
        logger.error("This usually means the server cannot be reached or the URI is incorrect")
        return False
    except pymongo.errors.ConfigurationError as e:
        logger.error(f"MongoDB Configuration Error: {str(e)}")
        logger.error("This usually indicates an issue with the connection string format")
        return False
    except pymongo.errors.ConnectionFailure as e:
        logger.error(f"MongoDB Connection Failure: {str(e)}")
        logger.error("This usually indicates network connectivity issues or incorrect credentials")
        return False
    except pymongo.errors.OperationFailure as e:
        logger.error(f"MongoDB Operation Failure: {str(e)}")
        logger.error(f"Error Code: {e.code if hasattr(e, 'code') else 'Unknown'}")
        logger.error("This usually indicates authentication or authorization issues")
        return False
    except Exception as e:
        logger.error(f"Unexpected MongoDB error: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        if client:
            try:
                client.close()
                logger.debug("MongoDB client closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB client: {str(e)}")
async def main():
    logger.info("Starting Credential Tests")
    
    results = {
        "AWS": await test_aws_credentials(),
        "Cognito": await test_cognito_configuration(),
        "JWT": await test_jwt_token(),
        "PostgreSQL": await test_postgres_connection(),
        "MongoDB": await test_mongodb_connection()
    }
    
    logger.info("\nTest Results:")
    for service, success in results.items():
        status = "✓ Passed" if success else "✗ Failed"
        logger.info(f"{service}: {status}")
    
    if not all(results.values()):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
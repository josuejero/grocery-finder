import asyncio
import logging
import os
import socket
import subprocess
import sys
from pathlib import Path

import psycopg2
from dotenv import dotenv_values

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("credential_tests.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

for key in [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
]:
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


def check_network_connectivity(host, port):
    logger.debug(f"Checking network connectivity to {host}:{port}")

    try:
        logger.debug("Running traceroute...")
        result = subprocess.run(
            ["traceroute", host], capture_output=True, text=True, timeout=10
        )
        logger.debug(f"Traceroute result:\n{result.stdout}")
    except Exception as e:
        logger.debug(f"Traceroute failed: {str(e)}")

    try:
        logger.debug(f"Testing TCP connection to port {port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(port)))
        if result == 0:
            logger.debug(f"Port {port} is open")
        else:
            logger.debug(f"Port {port} is closed (code: {result})")
        sock.close()
    except Exception as e:
        logger.debug(f"Port check failed: {str(e)}")

    try:
        logger.debug("Checking SSL certificate...")
        import ssl

        context = ssl.create_default_context()
        with context.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(5)
            s.connect((host, port))
            cert = s.getpeercert()
            logger.debug(f"SSL Certificate: {cert}")
    except Exception as e:
        logger.debug(f"SSL check failed: {str(e)}")


async def test_postgres_connection():
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")

    logger.debug(f"Testing PostgreSQL connection to: {host}:{port}")
    logger.debug(f"Database: {db}")
    logger.debug(f"User: {user}")

    check_network_connectivity(host, int(port))

    try:
        try:
            ip_address = socket.gethostbyname(host)
            logger.debug(f"Successfully resolved {host} to {ip_address}")

            ip_parts = ip_address.split(".")
            if (
                ip_parts[0] == "10"
                or (ip_parts[0] == "172" and 16 <= int(ip_parts[1]) <= 31)
                or (ip_parts[0] == "192" and ip_parts[1] == "168")
            ):
                logger.warning("RDS instance has private IP. Ensure VPC connection")
        except socket.gaierror as e:
            logger.error(f"Failed to resolve hostname {host}: {str(e)}")
            return False

        logger.debug("Attempting PostgreSQL connection with SSL...")
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
            "sslmode": "require",
        }

        try:
            conn = psycopg2.connect(**conn_params)
        except psycopg2.OperationalError as ssl_error:
            logger.debug(f"SSL connection failed, trying without SSL: {str(ssl_error)}")
            conn_params["sslmode"] = "disable"
            conn = psycopg2.connect(**conn_params)

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        logger.debug(f"PostgreSQL version: {version[0]}")

        cursor.close()
        conn.close()

        logger.info("PostgreSQL Connection Successful")
        return True

    except psycopg2.OperationalError as e:
        logger.error(f"PostgreSQL Operational Error: {str(e)}")
        if "password authentication failed" in str(e).lower():
            logger.error("Authentication failed. Check credentials.")
        elif "connection refused" in str(e).lower():
            logger.error("Connection refused. Check database status.")
        elif "timeout expired" in str(e).lower():
            logger.error("Connection timeout. Check security settings.")
        return False
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        return False


async def main():
    logger.info("Starting PostgreSQL Credential Test")

    try:
        result = await test_postgres_connection()
        status = "✓ Passed" if result else "✗ Failed"
        logger.info(f"PostgreSQL Connection Test: {status}")
    except Exception as e:
        logger.error(f"Test failed with unexpected error: {str(e)}")

    logger.info("PostgreSQL Credential Test Completed")


if __name__ == "__main__":
    asyncio.run(main())

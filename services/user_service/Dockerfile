FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create log directory with proper permissions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gcc \
        python3-dev \
        libpq-dev \
        netcat-traditional && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    mkdir -p /var/log/user_service && \
    chown -R nobody:nogroup /var/log/user_service && \
    chmod -R 777 /var/log/user_service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
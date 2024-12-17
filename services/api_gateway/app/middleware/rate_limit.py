from fastapi import Request, HTTPException, status
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import logger

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host
        endpoint = request.url.path
        rate_limit = settings.RATE_LIMIT_PER_MINUTE
        key = f"rate_limit:{client_ip}:{endpoint}"
        try:
            requests = await self.redis_client.get(key)
            if requests and int(requests) >= rate_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests"
                )
            pipe = self.redis_client.pipeline()
            await pipe.incr(key, 1)
            await pipe.expire(key, 60)
            await pipe.execute()
        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiting: {e}")
        response = await call_next(request)
        return response

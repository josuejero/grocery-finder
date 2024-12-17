# app/services/gateway_service.py
import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger
from app.core.service_utils import handle_http_error

class GatewayService:
    async def forward_request(self, method: str, endpoint: str, headers: dict = None, json: dict = None, params: dict = None):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method=method,
                    url=f"{settings.USER_SERVICE_URL}{endpoint}",
                    headers=headers,
                    json=json,
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            handle_http_error(e)

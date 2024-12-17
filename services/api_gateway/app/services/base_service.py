# app/services/base_service.py
from fastapi import HTTPException, status
import httpx
from typing import Dict, Any, Optional
from app.core.logging import logger
from app.core.service_utils import handle_http_error  # Import the utility

class BaseService:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=f"{self.base_url}/{endpoint}",
                    headers=headers,
                    json=data if method.upper() != 'GET' else None,
                    params=params if method.upper() == 'GET' else None,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            handle_http_error(e)  # Use the extracted utility

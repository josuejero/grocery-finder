# app/services/auth_service.py
from .base_service import BaseService
from app.core.config import settings
from typing import Dict, Any


class AuthService(BaseService):
    def __init__(self):
        super().__init__(settings.AUTH_SERVICE_URL)

    async def login(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        return await self._make_request(
            method="POST",
            endpoint="token",
            data=credentials
        )

    async def register(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._make_request(
            method="POST",
            endpoint="register",
            data=user_data
        )
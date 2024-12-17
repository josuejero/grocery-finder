# app/services/user_service.py
from typing import Dict, Any
from app.services.base_service import BaseService
from app.core.config import settings

class UserService(BaseService):
    def __init__(self):
        super().__init__(settings.USER_SERVICE_URL)

    async def get_profile(self, token: str) -> Dict[str, Any]:
        return await self._make_request(
            method="GET",
            endpoint="users/me",
            headers={"Authorization": f"Bearer {token}"}
        )

    async def create_shopping_list(self, token: str, list_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._make_request(
            method="POST",
            endpoint="users/me/shopping-lists",
            headers={"Authorization": f"Bearer {token}"},
            data=list_data
        )

    async def get_shopping_lists(self, token: str) -> Dict[str, Any]:
        return await self._make_request(
            method="GET",
            endpoint="users/me/shopping-lists",
            headers={"Authorization": f"Bearer {token}"}
        )
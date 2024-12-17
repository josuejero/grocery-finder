# app/services/price_service.py
from typing import Dict, Any, Optional
from app.services.base_service import BaseService
from app.core.config import settings

class PriceService(BaseService):
    def __init__(self):
        super().__init__(settings.PRICE_SERVICE_URL)

    async def get_price_comparison(self, product_id: str) -> Dict[str, Any]:
        return await self._make_request(
            method="GET", 
            endpoint=f"prices/compare/{product_id}"
        )

    async def create_price_entry(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._make_request(
            method="POST", 
            endpoint="prices", 
            data=price_data
        )

    async def get_price_history(
        self, 
        product_id: str, 
        store_id: Optional[str] = None
    ) -> Dict[str, Any]:
        params = {"store_id": store_id} if store_id else None
        return await self._make_request(
            method="GET", 
            endpoint=f"prices/history/{product_id}",
            params=params
        )
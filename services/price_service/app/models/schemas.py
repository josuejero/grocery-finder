# services/price_service/app/models/schemas.py
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator
from decimal import Decimal

class StoreLocation(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., description="[longitude, latitude]")

    @validator("coordinates")
    def validate_coordinates(cls, v):
        if len(v) != 2:
            raise ValueError("Coordinates must be [longitude, latitude]")
        lon, lat = v
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            raise ValueError("Invalid coordinates range")
        return v

class Store(BaseModel):
    id: str
    name: str
    location: StoreLocation
    address: str
    active: bool = True
    business_hours: Optional[Dict[str, str]] = None
    phone: Optional[str] = None
    website: Optional[str] = None

class Product(BaseModel):
    id: str
    name: str
    category: str
    brand: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    barcode: Optional[str] = None
    tags: List[str] = []
    active: bool = True

class PriceEntry(BaseModel):
    store_id: str
    product_id: str
    price: Decimal = Field(..., ge=0)
    currency: str = "USD"
    timestamp: datetime
    unit: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    sale_price: Optional[Decimal] = Field(None, ge=0)
    sale_end_date: Optional[datetime] = None

    @validator("sale_price")
    def validate_sale_price(cls, v, values):
        if v is not None and "price" in values and v >= values["price"]:
            raise ValueError("Sale price must be less than regular price")
        return v

class PriceHistory(BaseModel):
    product_id: str
    store_id: str
    history: List[PriceEntry]
    average_price: Decimal
    min_price: Decimal
    max_price: Decimal
    price_trend: str  # "increasing", "decreasing", or "stable"

class PriceComparison(BaseModel):
    product_id: str
    timestamp: datetime
    store_prices: List[Dict[str, Decimal]]
    best_price: Decimal
    best_store_id: str
    price_difference_percentage: Dict[str, float]

class ProductFilter(BaseModel):
    category: Optional[str] = None
    brand: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    store_id: Optional[str] = None
    on_sale: Optional[bool] = None
    sort_by: Optional[str] = "price"  # "price", "name", "brand"
    sort_order: Optional[str] = "asc"  # "asc" or "desc"
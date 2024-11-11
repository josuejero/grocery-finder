from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class ShoppingListItem(BaseModel):
    name: str
    quantity: int
    notes: Optional[str] = None

class ShoppingListBase(BaseModel):
    name: str
    items: List[ShoppingListItem] = []

class ShoppingListCreate(ShoppingListBase):
    pass

class ShoppingList(ShoppingListBase):
    id: int
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)

class ShoppingListUpdate(BaseModel):
    name: Optional[str] = None
    items: Optional[List[ShoppingListItem]] = None
    is_active: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)
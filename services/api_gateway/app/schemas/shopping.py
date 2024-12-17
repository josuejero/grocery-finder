from typing import List, Optional
from pydantic import BaseModel

class ShoppingListItem(BaseModel):
    name: str
    quantity: int
    notes: Optional[str] = None

class ShoppingList(BaseModel):
    id: int
    name: str
    items: List[ShoppingListItem]

class ShoppingListCreate(BaseModel):
    name: str
    items: List[ShoppingListItem]
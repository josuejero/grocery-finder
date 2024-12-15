# services/user_service/app/schemas/__init__.py
from .user import UserBase, UserCreate, UserUpdate
from .profile import UserProfile, UserPreferencesUpdate, UserProfileUpdate
from .shopping_list import ShoppingListBase, ShoppingListCreate, ShoppingList, ShoppingListUpdate

__all__ = [
    'UserBase', 
    'UserCreate', 
    'UserProfile',
    'UserUpdate',
    'UserPreferencesUpdate',
    'UserProfileUpdate',
    'ShoppingListBase',
    'ShoppingListCreate',
    'ShoppingList',
    'ShoppingListUpdate'
]
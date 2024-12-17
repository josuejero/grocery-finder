# app/core/decorators.py
import functools
from typing import Callable, Any
from fastapi import HTTPException
from app.core.logging import logger
from app.core.errors import BaseServiceError

def handle_service_errors(func: Callable) -> Callable:
    """
    Decorator to handle common service-related errors
    
    Args:
        func (Callable): The method to be decorated
    
    Returns:
        Callable: Wrapped method with error handling
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except BaseServiceError:
            # Re-raise BaseServiceError as-is
            raise
        except HTTPException:
            # Re-raise HTTPException as-is
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise BaseServiceError(
                detail=f"An unexpected error occurred: {str(e)}"
            )
    return wrapper
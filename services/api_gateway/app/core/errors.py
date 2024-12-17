# app/core/errors.py
from fastapi import HTTPException, status
from typing import Optional, Any, Dict

class BaseServiceError(HTTPException):
    """Base class for all service-related errors"""
    def __init__(
        self, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, 
        detail: str = "An unexpected error occurred",
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(
            status_code=status_code, 
            detail=detail, 
            headers=headers
        )

class ServiceUnavailableError(BaseServiceError):
    """Error raised when a service is unavailable"""
    def __init__(self, service_name: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service_name} service is currently unavailable"
        )

class AuthenticationError(BaseServiceError):
    """Error raised for authentication-related issues"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class ValidationError(BaseServiceError):
    """Error raised for validation failures"""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )

class ResourceNotFoundError(BaseServiceError):
    """Error raised when a requested resource is not found"""
    def __init__(self, resource: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found"
        )
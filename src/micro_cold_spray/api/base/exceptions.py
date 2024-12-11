"""Base exceptions for all API modules."""

from typing import Dict, Any, Optional


class APIError(Exception):
    """Base exception for all API errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


class ServiceError(APIError):
    """Base exception for service-level errors."""
    pass


class ValidationError(APIError):
    """Base exception for validation errors."""
    pass

"""Data collection exceptions."""

from typing import Dict, Any
from ..base.exceptions import ServiceError


class DataCollectionError(ServiceError):
    """Data collection specific errors."""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message, context)


class StorageError(DataCollectionError):
    """Storage-related errors."""
    pass

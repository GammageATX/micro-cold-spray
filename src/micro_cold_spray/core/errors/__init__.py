"""Error handling package.

Provides error handling utilities for the application including:
- Error codes and HTTP status mapping
- Error formatting and response generation
- Domain-specific exceptions
"""

from .codes import AppErrorCode
from .formatting import format_error, format_service_error, raise_http_error
from .exceptions import (
    ServiceError,
    ValidationError,
    ConfigurationError,
    CommunicationError,
    HardwareError,
    DataCollectionError,
    StateError,
    ProcessError,
    MessageError
)

__all__ = [
    # Error codes
    'AppErrorCode',
    
    # Error formatting
    'format_error',
    'format_service_error',
    'raise_http_error',
    
    # Exceptions
    'ServiceError',
    'ValidationError',
    'ConfigurationError',
    'CommunicationError',
    'HardwareError',
    'DataCollectionError',
    'StateError',
    'ProcessError',
    'MessageError'
]

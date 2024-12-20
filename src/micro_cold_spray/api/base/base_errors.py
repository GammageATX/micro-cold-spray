"""Base error handling utilities."""

from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status


def create_error(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    context: Optional[dict[str, Any]] = None,
    cause: Optional[Exception] = None,
) -> HTTPException:
    """Create an HTTP error with consistent format."""
    error = HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        },
    )
    if cause:
        error.__cause__ = cause
    return error


class ConfigError(HTTPException):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize config error."""
        detail = {
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        }
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
        if cause:
            self.__cause__ = cause

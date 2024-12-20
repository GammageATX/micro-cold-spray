"""Simple error handling for FastAPI services."""

from fastapi import HTTPException, status


def create_error(status_code: int, message: str) -> HTTPException:
    """Create a simple HTTP exception.
    
    Args:
        status_code: HTTP status code
        message: Error message
        
    Returns:
        HTTPException: The error to raise
    """
    return HTTPException(
        status_code=status_code,
        detail=message
    )

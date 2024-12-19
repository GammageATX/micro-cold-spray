"""Shared dependencies for communication API."""

from fastapi import HTTPException, status

from .service import CommunicationService


def get_service() -> CommunicationService:
    """Get service instance."""
    from .router import _service  # Import here to avoid circular dependency
    
    if not _service or not _service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CommunicationService not initialized"
        )
    return _service

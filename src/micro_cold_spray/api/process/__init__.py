"""Process API package."""

from fastapi import Request
from micro_cold_spray.api.process.process_service import ProcessService


async def get_process_service(request: Request) -> ProcessService:
    """Get process service instance from app state."""
    return request.app.state.service


__all__ = [
    "ProcessService",
    "get_process_service"
]

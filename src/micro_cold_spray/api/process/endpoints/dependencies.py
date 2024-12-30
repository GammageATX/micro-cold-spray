"""Common dependencies for process endpoints."""

from fastapi import Depends
from micro_cold_spray.api.process.process_service import ProcessService


def get_service(process_service: ProcessService = Depends()) -> ProcessService:
    """Get process service instance."""
    return process_service

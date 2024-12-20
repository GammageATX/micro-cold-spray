"""Validation application module."""

from typing import Optional

from fastapi import FastAPI

from micro_cold_spray.api.base.base_app import create_app
from micro_cold_spray.api.validation.validation_service import ValidationService


def create_validation_app(
    service_name: Optional[str] = None,
    service_dir: Optional[str] = None,
    **kwargs
) -> FastAPI:
    """Create validation application.
    
    Args:
        service_name: Optional service name
        service_dir: Optional service directory
        **kwargs: Additional FastAPI arguments
        
    Returns:
        FastAPI application
    """
    return create_app(
        service_class=ValidationService,
        title="Validation API",
        service_name=service_name,
        service_dir=service_dir,
        **kwargs
    )

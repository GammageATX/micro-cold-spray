"""Test fixtures package.

This package contains shared test fixtures used across test modules:

Base Fixtures:
    - MockBaseService: Base service implementation for testing
    - test_app: FastAPI test application fixture
    - async_client: Async HTTP test client
"""

from .base import (
    MockBaseService,
    test_app,
    async_client,
)

__all__ = [
    "MockBaseService",
    "test_app",
    "async_client",
]

"""Core test fixtures and configuration."""

import pytest
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, PropertyMock
from datetime import datetime

from micro_cold_spray.core.base.models import ServiceStatus


@pytest.fixture
def mock_core_service():
    """Create mock core service with common attributes."""
    service = AsyncMock()
    type(service).is_initialized = PropertyMock(return_value=True)
    type(service).is_running = PropertyMock(return_value=True)
    type(service).status = PropertyMock(return_value=ServiceStatus.RUNNING)
    return service


@pytest.fixture
def mock_core_router():
    """Create mock core router with common attributes."""
    router = AsyncMock()
    type(router).is_initialized = PropertyMock(return_value=True)
    return router


@pytest.fixture
def core_test_data() -> Dict[str, Any]:
    """Common test data for core modules."""
    return {
        "test_id": "test-123",
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "version": "1.0.0",
            "type": "test"
        },
        "data": {
            "key": "value",
            "number": 42
        }
    }


@pytest.fixture(autouse=True)
def setup_core_test_env() -> Generator[None, None, None]:
    """Setup core test environment before each test."""
    # Clear any core module registries or caches
    from micro_cold_spray.core.base.registry import ServiceRegistry
    ServiceRegistry.clear()
    yield

"""Common test fixtures and configuration."""

import pytest
import asyncio
from pathlib import Path
from typing import Generator, Any

from micro_cold_spray.api.base import BaseService


@pytest.fixture
def base_service() -> Generator[BaseService, None, None]:
    """Create a base service instance."""
    service = BaseService("test_service")
    yield service
    asyncio.run(service.stop())


@pytest.fixture
def test_config() -> dict[str, Any]:
    """Test configuration data."""
    return {
        "key": "value",
        "number": 123,
        "nested": {
            "inner": "data"
        }
    }


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture(autouse=True)
def setup_test_env() -> Generator[None, None, None]:
    """Setup test environment before each test."""
    # Clear service registry
    from micro_cold_spray.api.base import _services
    _services.clear()
    yield

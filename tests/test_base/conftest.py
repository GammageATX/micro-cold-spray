"""Base-specific test fixtures."""

import pytest
import asyncio
from typing import Generator
from unittest.mock import AsyncMock, PropertyMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware

from micro_cold_spray.api.base import BaseService


@pytest.fixture
def base_service() -> Generator[BaseService, None, None]:
    """Create a base service instance."""
    service = BaseService("test_service")
    yield service
    asyncio.run(service.stop())


@pytest.fixture
def mock_base_service():
    """Create mock base service."""
    service = AsyncMock(spec=BaseService)
    type(service).is_initialized = PropertyMock(return_value=True)
    type(service).is_running = PropertyMock(return_value=True)
    type(service)._service_name = PropertyMock(return_value="TestService")
    type(service).version = PropertyMock(return_value="1.0.0")
    type(service).uptime = PropertyMock(return_value="0:00:00")
    
    # Mock health check method
    async def mock_check_health():
        return {
            "status": "ok",
            "service_info": {
                "name": service._service_name,
                "version": service.version,
                "uptime": str(service.uptime),
                "running": service.is_running
            }
        }
    service.check_health = AsyncMock(side_effect=mock_check_health)
    
    return service


@pytest.fixture
def test_app_client(mock_base_service):
    """Create test FastAPI app with client."""
    app = FastAPI()
    app.state.service = mock_base_service
    return TestClient(app)


@pytest.fixture
def test_app_with_cors(mock_base_service):
    """Create test FastAPI app with CORS middleware."""
    app = FastAPI()
    app.state.service = mock_base_service
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

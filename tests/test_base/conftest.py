"""Base module test configuration and fixtures."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from typing import Optional, Generator, AsyncGenerator, Any

from micro_cold_spray.api.base.base_app import create_app
from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_configurable import ConfigurableService


class TestModel(BaseModel):
    """Test model for router testing."""
    id: int
    name: str
    value: float = Field(ge=0.0)


class TestConfig(BaseModel):
    """Test configuration model."""
    value: int = Field(ge=0)
    name: str = Field(default="test")
    required_field: str


class MockBaseService(BaseService):
    """Mock base service for testing."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


class FailingService(BaseService):
    """Service that fails to start/stop."""
    
    async def _start(self) -> None:
        """Start implementation that fails."""
        raise ValueError("Failed to start")
        
    async def _stop(self) -> None:
        """Stop implementation that fails."""
        raise ValueError("Failed to stop")


class ErrorService(BaseService):
    """Service that raises errors during health checks."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        raise ValueError("Failed to stop")


class TestRouterService(BaseService):
    """Test service for router."""
    
    def __init__(self, name: Optional[str] = None) -> None:
        """Initialize service."""
        super().__init__(name)
        self.router = None
        
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


class ErrorRouterService(BaseService):
    """Service that fails health checks."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False
        
    async def health(self) -> dict:
        """Health check that raises error."""
        raise ValueError("Health check failed")


class TestRegistryService(BaseService):
    """Test service for registry."""
    
    async def _start(self) -> None:
        """Start implementation."""
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


class TestConfigurableService(ConfigurableService):
    """Test configurable service."""
    config_model = TestConfig
    
    def __init__(self, name: Optional[str] = None) -> None:
        """Initialize service."""
        super().__init__(config_model=TestConfig)
        self._name = name or self.__class__.__name__.lower()
        self._is_running = False
        self._is_configured = False

    async def _start(self) -> None:
        """Start implementation."""
        if not self.is_configured:
            return
        self._is_running = True
        
    async def _stop(self) -> None:
        """Stop implementation."""
        self._is_running = False


class InvalidConfigurableService(ConfigurableService):
    """Invalid configurable service without config model."""
    pass


@pytest.fixture
async def app() -> FastAPI:
    """Create test application."""
    app = create_app(
        service_class=MockBaseService,
        title="Test API",
        service_name="test"
    )
    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, Any, None]:
    """Create test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_model() -> TestModel:
    """Create test model."""
    return TestModel(id=1, name="test", value=42.0)


@pytest.fixture
def test_config() -> TestConfig:
    """Create test configuration."""
    return TestConfig(value=42, name="test", required_field="required")

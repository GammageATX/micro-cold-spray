"""Tests for service registry functionality."""

import pytest
from micro_cold_spray.api.base import (
    BaseService,
    get_service,
    register_service
)


class TestServiceRegistry:
    """Test service registry functionality."""
    
    def test_register_get_service(self):
        """Test service registration and retrieval."""
        service = BaseService("test_service")
        register_service(service)
        
        # Get service
        service_getter = get_service(BaseService)
        retrieved = service_getter()
        assert retrieved is service
        
    def test_unregistered_service(self):
        """Test getting unregistered service."""
        # Clear any registered services first
        from micro_cold_spray.api.base import _services
        _services.clear()
        
        with pytest.raises(RuntimeError, match="Service.*not initialized"):
            getter = get_service(BaseService)
            getter()

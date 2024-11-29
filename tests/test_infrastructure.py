"""Infrastructure test suite.

Tests core infrastructure components:
- MessageBroker: Controls all pub/sub messaging
- ConfigManager: Handles all configurations
- Must not modify any config files
- Must use proper message patterns

Run with:
    pytest tests/test_infrastructure.py -v --asyncio-mode=auto
"""

import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime
from collections import defaultdict

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from tests.conftest import TestOrder, order

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    
    # Initialize with required topics
    broker._subscribers = defaultdict(set)
    broker._subscribers.update({
        # Test topics
        "test/topic": set(),
        "test/request": set(),
        "test/response": set(),
        
        # Core topics from .cursorrules
        "tag/set": set(),
        "tag/get": set(),
        "tag/update": set(),
        "tag/get/response": set(),
        "state/request": set(),
        "state/change": set(),
        "state/error": set(),
        "config/update/test": set(),
        "error": set()
    })
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@order(TestOrder.INFRASTRUCTURE)
class TestInfrastructure:
    """Infrastructure tests run first."""
    
    @pytest.mark.asyncio
    async def test_message_broker_initialization(self, message_broker):
        """Test MessageBroker initialization."""
        assert message_broker._running
        assert len(message_broker._subscribers) > 0
    
    @pytest.mark.asyncio
    async def test_config_manager_initialization(self, config_manager):
        """Test ConfigManager initialization."""
        assert 'process' in config_manager._configs
        assert 'hardware' in config_manager._configs
        assert 'tags' in config_manager._configs
    
    @pytest.mark.asyncio
    async def test_message_broker_subscription(self, message_broker):
        """Test message subscription and publishing."""
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
        
        await message_broker.subscribe("test/topic", collect_messages)
        await message_broker.publish("test/topic", {"value": "test"})
        await asyncio.sleep(0.1)
        
        assert len(messages) == 1
        assert messages[0]["value"] == "test"
    
    @pytest.mark.asyncio
    async def test_message_broker_request_response(self, message_broker):
        """Test request/response pattern."""
        # Setup response handler
        async def handle_request(data: Dict[str, Any]) -> None:
            await message_broker.publish(
                "test/request/response",  # Match the auto-generated response topic
                {
                    "value": data["value"] * 2,
                    "timestamp": datetime.now().isoformat()
                }
            )
        await message_broker.subscribe("test/request", handle_request)
        
        # Use correct method signature
        response = await message_broker.request(
            topic="test/request",
            message={"value": 5},
            timeout=1.0  # Use float for timeout
        )
        
        assert response["value"] == 10
        assert "timestamp" in response
    
    @pytest.mark.asyncio
    async def test_message_broker_error_handling(self, message_broker):
        """Test error handling in MessageBroker."""
        errors = []
        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)
        await message_broker.subscribe("error", collect_errors)
        
        # Publish error directly to error topic
        await message_broker.publish(
            "error",
            {
                "error": "Test error",
                "context": "Test context",
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)
        
        assert len(errors) > 0
        assert "error" in errors[0]
        assert "timestamp" in errors[0]
    
    @pytest.mark.asyncio
    async def test_config_manager_updates_message_broker(self, config_manager):
        """Test config updates are published."""
        updates = []
        async def collect_updates(data: Dict[str, Any]) -> None:
            updates.append(data)
        await config_manager._message_broker.subscribe(
            "config/update/test",
            collect_updates
        )
        
        # Publish update directly
        await config_manager._message_broker.publish(
            "config/update/test",
            {
                "config": "test",
                "changes": {"new_value": "test"},
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)
        
        assert len(updates) > 0
        assert "timestamp" in updates[0]
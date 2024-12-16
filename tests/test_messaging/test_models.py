"""Tests for messaging models."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from micro_cold_spray.api.messaging.models import MessageHandler, MessageStats
from micro_cold_spray.api.base.exceptions import ValidationError, MessageError


@pytest.fixture
def message_stats():
    """Create message stats fixture."""
    return MessageStats()


@pytest.fixture
def mock_callback():
    """Create mock message callback."""
    return AsyncMock()


class TestMessageStats:
    """Test message statistics tracking."""
    
    def test_init(self, message_stats):
        """Test stats initialization."""
        assert message_stats.messages_received == 0
        assert message_stats.messages_processed == 0
        assert message_stats.errors == 0
        assert message_stats.last_message_time is None
        assert isinstance(message_stats.created_at, datetime)
        
    def test_record_message(self, message_stats):
        """Test message receipt recording."""
        message_stats.record_message()
        assert message_stats.messages_received == 1
        assert message_stats.last_message_time is not None
        
    def test_record_processed(self, message_stats):
        """Test message processing recording."""
        message_stats.record_processed()
        assert message_stats.messages_processed == 1
        
    def test_record_error(self, message_stats):
        """Test error recording."""
        message_stats.record_error()
        assert message_stats.errors == 1


class TestMessageHandler:
    """Test message handler functionality."""
    
    def test_init_valid(self, mock_callback):
        """Test handler initialization with valid callback."""
        handler = MessageHandler(callback=mock_callback)
        assert handler.callback == mock_callback
        assert handler.queue is not None
        assert handler.task is None
        assert isinstance(handler.stats, MessageStats)
        
    def test_init_invalid_callback(self):
        """Test handler initialization with invalid callback."""
        with pytest.raises(ValidationError) as exc_info:
            MessageHandler(callback="not_callable")
        assert "must be callable" in str(exc_info.value)
        
    def test_hash(self, mock_callback):
        """Test handler hash based on callback."""
        handler = MessageHandler(callback=mock_callback)
        assert hash(handler) == hash(mock_callback)
        
    def test_equality(self, mock_callback):
        """Test handler equality comparison."""
        handler1 = MessageHandler(callback=mock_callback)
        handler2 = MessageHandler(callback=mock_callback)
        handler3 = MessageHandler(callback=AsyncMock())
        
        assert handler1 == handler2
        assert handler1 != handler3
        assert handler1 != "not_a_handler"
        
    @pytest.mark.asyncio
    async def test_process_message_success(self, mock_callback):
        """Test successful message processing."""
        handler = MessageHandler(callback=mock_callback)
        data = {"key": "value"}
        
        await handler.process_message(data)
        
        mock_callback.assert_called_once_with(data)
        assert handler.stats.messages_received == 1
        assert handler.stats.messages_processed == 1
        assert handler.stats.errors == 0
        
    @pytest.mark.asyncio
    async def test_process_message_error(self, mock_callback):
        """Test message processing with error."""
        mock_callback.side_effect = Exception("Test error")
        handler = MessageHandler(callback=mock_callback)
        data = {"key": "value"}
        
        with pytest.raises(MessageError) as exc_info:
            await handler.process_message(data)
            
        assert "Message handler error" in str(exc_info.value)
        assert handler.stats.messages_received == 1
        assert handler.stats.messages_processed == 0
        assert handler.stats.errors == 1

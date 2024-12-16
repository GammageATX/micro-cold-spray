"""Tests for messaging models."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
import asyncio

from micro_cold_spray.api.messaging.models import MessageStats, MessageHandler
from micro_cold_spray.api.base.exceptions import ValidationError, MessageError


class TestMessageStats:
    """Test message statistics tracking."""

    def test_init(self):
        """Test initialization of message stats."""
        stats = MessageStats()
        assert stats.messages_received == 0
        assert stats.messages_processed == 0
        assert stats.errors == 0
        assert stats.last_message_time is None
        assert isinstance(stats.created_at, datetime)

    def test_record_message(self):
        """Test recording received message."""
        stats = MessageStats()
        stats.record_message()
        assert stats.messages_received == 1
        assert isinstance(stats.last_message_time, datetime)

        # Record another message
        stats.record_message()
        assert stats.messages_received == 2

    def test_record_processed(self):
        """Test recording processed message."""
        stats = MessageStats()
        stats.record_processed()
        assert stats.messages_processed == 1

        # Record another processed message
        stats.record_processed()
        assert stats.messages_processed == 2

    def test_record_error(self):
        """Test recording error."""
        stats = MessageStats()
        stats.record_error()
        assert stats.errors == 1

        # Record another error
        stats.record_error()
        assert stats.errors == 2


class TestMessageHandler:
    """Test message handler functionality."""

    def test_init_valid(self):
        """Test initialization with valid callback."""
        def callback(data): pass
        handler = MessageHandler(callback=callback)
        assert handler.callback == callback
        assert isinstance(handler.queue, asyncio.Queue)
        assert handler.task is None
        assert isinstance(handler.stats, MessageStats)

    def test_init_invalid(self):
        """Test initialization with invalid callback."""
        with pytest.raises(ValidationError) as exc_info:
            MessageHandler(callback="not_callable")
        assert "must be callable" in str(exc_info.value)
        assert exc_info.value.context["callback_type"] == str

    def test_hash(self):
        """Test handler hash based on callback."""
        def callback1(data): pass
        def callback2(data): pass
        
        handler1 = MessageHandler(callback=callback1)
        handler2 = MessageHandler(callback=callback2)
        handler3 = MessageHandler(callback=callback1)
        
        assert hash(handler1) != hash(handler2)
        assert hash(handler1) == hash(handler3)

    def test_equality(self):
        """Test handler equality based on callback."""
        def callback1(data): pass
        def callback2(data): pass
        
        handler1 = MessageHandler(callback=callback1)
        handler2 = MessageHandler(callback=callback2)
        handler3 = MessageHandler(callback=callback1)
        
        assert handler1 != handler2
        assert handler1 == handler3
        assert handler1 != "not_a_handler"

    @pytest.mark.asyncio
    async def test_process_message_success(self):
        """Test successful message processing."""
        mock_callback = AsyncMock()
        handler = MessageHandler(callback=mock_callback)
        test_data = {"key": "value"}
        
        await handler.process_message(test_data)
        
        mock_callback.assert_called_once_with(test_data)
        assert handler.stats.messages_received == 1
        assert handler.stats.messages_processed == 1
        assert handler.stats.errors == 0
        assert isinstance(handler.stats.last_message_time, datetime)

    @pytest.mark.asyncio
    async def test_process_message_error(self):
        """Test message processing with error."""
        mock_callback = AsyncMock(side_effect=ValueError("Test error"))
        handler = MessageHandler(callback=mock_callback)
        test_data = {"key": "value"}
        
        with pytest.raises(MessageError) as exc_info:
            await handler.process_message(test_data)
        
        assert "Message handler error" in str(exc_info.value)
        assert exc_info.value.context["error"] == "Test error"
        assert handler.stats.messages_received == 1
        assert handler.stats.messages_processed == 0
        assert handler.stats.errors == 1

    @pytest.mark.asyncio
    async def test_process_message_with_sync_callback(self):
        """Test message processing with synchronous callback."""
        processed_data = []

        def sync_callback(data):
            processed_data.append(data)
            
        handler = MessageHandler(callback=sync_callback)
        test_data = {"key": "value"}
        
        await handler.process_message(test_data)
        
        assert processed_data == [test_data]
        assert handler.stats.messages_received == 1
        assert handler.stats.messages_processed == 1
        assert handler.stats.errors == 0

    @pytest.mark.asyncio
    async def test_queue_operations(self):
        """Test message queue operations."""
        handler = MessageHandler(callback=AsyncMock())
        test_data = {"key": "value"}
        
        # Test queue put/get
        await handler.queue.put(test_data)
        assert handler.queue.qsize() == 1
        data = await handler.queue.get()
        assert data == test_data

    @pytest.mark.asyncio
    async def test_task_lifecycle(self):
        """Test task creation and cleanup."""
        async def async_callback(data): pass
        handler = MessageHandler(callback=async_callback)
        
        # Create task
        handler.task = asyncio.create_task(handler.process_message({"key": "value"}))
        assert not handler.task.done()
        
        # Wait for task
        await handler.task
        assert handler.task.done()

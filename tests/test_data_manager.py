"""Data Manager test suite.

Tests data management according to .cursorrules:
- Run data collection
- Data compression
- Data backup
- Parameter history
- Error handling

Run with:
    pytest tests/test_data_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.data.data_manager import DataManager


@pytest.fixture
async def data_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[DataManager, None]:
    """Provide DataManager instance."""
    manager = DataManager(message_broker, config_manager)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@order(TestOrder.PROCESS)
class TestDataManager:
    """Data management tests run after process components."""

    @pytest.mark.asyncio
    async def test_data_compression(self, data_manager):
        """Test data compression."""
        # Track compression messages
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await data_manager._message_broker.subscribe(
            "data/compressed",
            collect_messages
        )

        # Send test data
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "values": [1.0, 2.0, 3.0]
        }
        await data_manager._message_broker.publish(
            "data/compress",
            test_data
        )
        await asyncio.sleep(0.1)

        # Verify compression
        assert len(messages) > 0
        assert messages[0]["original_size"] > messages[0]["compressed_size"]

    @pytest.mark.asyncio
    async def test_data_backup(self, data_manager, tmp_path):
        """Test data backup."""
        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()

        # Track backup messages
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await data_manager._message_broker.subscribe(
            "data/backup/complete",
            collect_messages
        )

        # Request backup
        await data_manager._message_broker.publish(
            "data/backup",
            {"path": str(backup_dir)}
        )
        await asyncio.sleep(0.1)

        # Verify backup
        assert len(messages) > 0
        assert messages[0]["backup_path"] == str(backup_dir)

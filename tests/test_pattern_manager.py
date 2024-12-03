# tests/test_pattern_manager.py

"""Pattern Manager test suite.

Tests pattern management according to .cursorrules:
- Pattern validation
- Pattern execution
- Parameter substitution
- Error handling

Run with:
    pytest tests/test_pattern_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from tests.conftest import TestOrder, order

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager


@pytest.fixture
async def pattern_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    process_validator: ProcessValidator
) -> AsyncGenerator[PatternManager, None]:
    """Provide PatternManager instance."""
    # Add motion config to hardware config
    config_manager._configs['hardware'] = {
        'motion': {
            'stage': {
                'dimensions': {
                    'x': 200.0,
                    'y': 200.0,
                    'z': 100.0
                },
                'speed': {
                    'max': 100.0,
                    'default': 50.0
                }
            }
        }
    }

    manager = PatternManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()


@order(TestOrder.PROCESS)
class TestPatternManager:
    """Pattern management tests."""

    @pytest.mark.asyncio
    async def test_pattern_validation(self, pattern_manager):
        """Test pattern validation."""
        # Track pattern messages
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await pattern_manager._message_broker.subscribe(
            "pattern/validation",
            collect_messages
        )

        # Send test pattern
        test_pattern = {
            "type": "line",
            "parameters": {
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 100.0, "y": 100.0}
            }
        }
        await pattern_manager._message_broker.publish(
            "pattern/validate",
            test_pattern
        )
        await asyncio.sleep(0.1)

        # Verify validation
        assert len(messages) > 0
        assert messages[0]["is_valid"]

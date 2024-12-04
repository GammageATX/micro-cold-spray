"""Process Validator test suite.

Tests process validation according to .cursorrules:
- Parameter validation
- Hardware state validation
- Motion limits validation
- Gas flow validation
- Vacuum level validation
- Pattern bounds validation
- Error handling

Run with:
    pytest tests/test_process_validator.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from datetime import datetime
from tests.conftest import TestOrder, order


@order(TestOrder.PROCESS)
class TestProcessValidator:
    """Process validation tests."""

    @pytest.mark.asyncio
    async def test_parameter_validation(self, process_validator):
        """Test parameter validation."""
        # Track validation responses
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_messages
        )

        # Send test parameters
        test_params = {
            "gas": {
                "type": "helium",
                "main_flow": 50.0,
                "carrier_flow": 2.0
            }
        }
        await process_validator._message_broker.publish(
            "validation/request",
            {
                "type": "parameters",
                "data": test_params
            }
        )
        await asyncio.sleep(0.1)

        # Verify validation
        assert len(messages) > 0
        assert messages[0]["result"]["valid"]
        assert messages[0]["request_type"] == "parameters"

    @pytest.mark.asyncio
    async def test_hardware_validation(self, process_validator):
        """Test hardware state validation."""
        # Track validation responses
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_messages
        )

        # Send test hardware state
        test_state = {
            "connection": True,
            "error": None,
            "position": {
                "x": 100.0,
                "y": 100.0,
                "z": 50.0
            }
        }
        await process_validator._message_broker.publish(
            "validation/request",
            {
                "type": "hardware",
                "data": test_state
            }
        )
        await asyncio.sleep(0.1)

        # Verify validation
        assert len(messages) > 0
        assert messages[0]["result"]["valid"]
        assert messages[0]["request_type"] == "hardware"

    @pytest.mark.asyncio
    async def test_validation_message_patterns(self, process_validator):
        """Test validation message patterns."""
        messages = []

        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)

        await process_validator._message_broker.subscribe(
            "validation/response",
            collect_messages
        )

        # Send test validation request
        await process_validator._message_broker.publish(
            "validation/request",
            {
                "type": "test",
                "data": {"value": 1.0},
                "timestamp": datetime.now().isoformat()
            }
        )
        await asyncio.sleep(0.1)

        # Verify message pattern
        assert len(messages) > 0
        assert "request_type" in messages[0]
        assert "result" in messages[0]
        assert "timestamp" in messages[0]
        assert not messages[0]["result"]["valid"]  # Unknown type should be invalid
        assert "Unknown validation type: test" in messages[0]["result"]["errors"]

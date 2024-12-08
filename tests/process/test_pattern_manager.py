# tests/test_pattern_manager.py

"""Pattern Manager test suite.

Tests pattern management according to .cursorrules:
- Pattern validation
- Pattern loading
- Pattern saving
- Error handling

Run with:
    pytest tests/operations/test_pattern_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from tests.conftest import TestOrder, order


@order(TestOrder.OPERATIONS)
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
        assert messages[0]["valid"]
        assert messages[0]["pattern"] == test_pattern

# tests/test_pattern_manager.py

"""Pattern Manager test suite.

Tests pattern management according to process.yaml:
- Pattern validation using process rules
- Pattern parameter validation
- Pattern preview generation
- Message pattern compliance
- Error handling

Pattern Types (from process.yaml):
- serpentine: Linear raster patterns
- spiral: Circular spiral patterns
- custom: Custom path patterns

Run with:
    pytest tests/test_pattern_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any
import asyncio
from datetime import datetime
from pathlib import Path
import yaml
from tests.conftest import TestOrder, order

@pytest.fixture
async def pattern_manager(
    message_broker,
    config_manager,
    process_validator
):
    """Provide PatternManager instance."""
    from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager
    
    manager = PatternManager(
        message_broker=message_broker,
        config_manager=config_manager,
        pattern_path=Path("data/patterns/library")
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@order(TestOrder.PROCESS)
class TestPatternManager:
    """Pattern management tests."""
    
    @pytest.mark.asyncio
    async def test_generate_serpentine_pattern(self, pattern_manager):
        """Test serpentine pattern generation."""
        # Create serpentine pattern using process.yaml parameters
        pattern = await pattern_manager.generate_serpentine(
            origin=[100.0, 100.0],
            length=50.0,
            spacing=2.0,
            speed=20.0,
            z_height=10.0,
            acceleration=1000.0,
            direction="x_first"
        )
        
        # Verify pattern structure matches process.yaml definition
        assert "pattern" in pattern
        assert "metadata" in pattern["pattern"]
        assert "params" in pattern["pattern"]
        assert pattern["pattern"]["type"] == "serpentine"
        assert pattern["pattern"]["params"]["length"] == 50.0
        assert pattern["pattern"]["params"]["spacing"] == 2.0
        assert pattern["pattern"]["params"]["direction"] == "x_first"

    @pytest.mark.asyncio
    async def test_generate_spiral_pattern(self, pattern_manager):
        """Test spiral pattern generation."""
        # Create spiral pattern using process.yaml parameters
        pattern = await pattern_manager.generate_spiral(
            origin=[100.0, 100.0],
            diameter=20.0,
            pitch=1.0,
            speed=20.0,
            z_height=10.0,
            acceleration=1000.0
        )
        
        # Verify pattern structure
        assert "pattern" in pattern
        assert "metadata" in pattern["pattern"]
        assert "params" in pattern["pattern"]
        assert pattern["pattern"]["type"] == "spiral"
        assert pattern["pattern"]["params"]["diameter"] == 20.0
        assert pattern["pattern"]["params"]["pitch"] == 1.0

    @pytest.mark.asyncio
    async def test_pattern_validation(self, pattern_manager):
        """Test pattern validation against process.yaml rules."""
        # Create pattern that exceeds sprayable area
        pattern_data = {
            "pattern": {
                "type": "serpentine",
                "params": {
                    "origin": [0.0, 0.0],  # Outside sprayable area
                    "length": 600.0,       # Exceeds limits
                    "spacing": 2.0,
                    "speed": 20.0,
                    "z_height": 10.0,
                    "acceleration": 1000.0,
                    "direction": "x_first"
                }
            }
        }
        
        # Track validation responses
        responses = []
        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)
        await pattern_manager._message_broker.subscribe(
            "patterns/error",
            collect_responses
        )
        await asyncio.sleep(0.1)  # Added sleep after subscribe
        
        # Attempt to validate invalid pattern
        with pytest.raises(Exception):
            await pattern_manager._validate_sprayable_area(pattern_data)
        await asyncio.sleep(0.1)  # Added sleep after validation
        
        # Verify error response
        assert len(responses) > 0
        assert "Pattern exceeds sprayable area" in str(responses[0]["error"])
        assert "timestamp" in responses[0]

    @pytest.mark.asyncio
    async def test_load_custom_pattern(self, pattern_manager, tmp_path):
        """Test loading custom pattern from CSV."""
        # Create test CSV file
        csv_path = tmp_path / "test_pattern.csv"
        csv_content = "x,y,z,velocity,dwell,spray_on\n"
        csv_content += "100,100,10,20,0,true\n"
        csv_content += "150,100,10,20,0,true\n"
        csv_path.write_text(csv_content)
        
        # Load custom pattern
        pattern = pattern_manager._load_custom_pattern(csv_path)
        
        # Verify pattern structure
        assert "pattern" in pattern
        assert "metadata" in pattern["pattern"]
        assert "moves" in pattern["pattern"]
        assert len(pattern["pattern"]["moves"]) == 2
        assert pattern["pattern"]["metadata"]["type"] == "custom"

    @pytest.mark.asyncio
    async def test_pattern_message_compliance(self, pattern_manager):
        """Test pattern-related message patterns."""
        # Track pattern messages
        messages = []
        async def collect_messages(data: Dict[str, Any]) -> None:
            messages.append(data)
            
        await pattern_manager._message_broker.subscribe(
            "patterns/loaded",
            collect_messages
        )
        await asyncio.sleep(0.1)  # Added sleep after subscribe
        
        # Create and load a pattern
        pattern = await pattern_manager.generate_serpentine(
            origin=[100.0, 100.0],
            length=50.0,
            spacing=2.0,
            speed=20.0,
            z_height=10.0,
            acceleration=1000.0,
            direction="x_first"
        )
        
        await pattern_manager.save_pattern(pattern, "test_pattern.yaml")
        await pattern_manager.load_pattern("serpentine", "test_pattern.yaml")
        await asyncio.sleep(0.1)  # Added sleep after operations
        
        # Verify message compliance
        assert len(messages) > 0
        assert "pattern" in messages[0]
        assert "type" in messages[0]
        assert "timestamp" in messages[0]
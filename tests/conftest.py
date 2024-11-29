"""Common test fixtures and configuration."""
import pytest
from enum import IntEnum
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import yaml

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager

class TestOrder(IntEnum):
    """Test execution order."""
    INFRASTRUCTURE = 100  # MessageBroker, ConfigManager, etc.
    PROCESS = 200        # ProcessValidator, ParameterManager, etc.
    UI = 300            # UIUpdateManager, widgets, etc.

def order(value: TestOrder):
    """Decorator to set test order."""
    def decorator(cls):
        cls.test_order = value
        return cls
    return decorator

@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide MessageBroker with required topics."""
    broker = MessageBroker()
    broker._subscribers = {
        # Core topics
        "tag/set": set(),
        "tag/get": set(),
        "tag/get/response": set(),
        "tag/update": set(),
        "state/change": set(),
        "state/request": set(),
        "state/error": set(),
        "error": set(),
        
        # Action topics
        "action/execute": set(),
        "action/status": set(),
        "action/complete": set(),
        "action/error": set(),
        
        # Parameter topics
        "parameters/load": set(),
        "parameters/save": set(),
        "parameters/loaded": set(),
        "parameters/saved": set(),
        "parameters/error": set(),
        
        # Pattern topics
        "patterns/load": set(),
        "patterns/save": set(),
        "patterns/loaded": set(),
        "patterns/saved": set(),
        "patterns/error": set(),
        
        # Sequence topics
        "sequence/load": set(),
        "sequence/save": set(),
        "sequence/start": set(),
        "sequence/stop": set(),
        "sequence/pause": set(),
        "sequence/resume": set(),
        "sequence/complete": set(),
        "sequence/error": set(),
        
        # Validation topics
        "validation/request": set(),
        "validation/response": set(),
        
        # Hardware topics
        "hardware/status/plc": set(),
        "hardware/status/motion": set(),
        "hardware/error": set()
    }
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[ConfigManager, None]:
    """Provide ConfigManager with test configurations."""
    manager = ConfigManager(message_broker)
    
    # Mock file operations to prevent any actual file changes
    manager._save_config = AsyncMock()
    manager.update_config = AsyncMock()
    manager._load_config = AsyncMock()
    manager.save_backup = AsyncMock()
    
    # Load test configs
    with open("config/process.yaml") as f:
        process_config = yaml.safe_load(f)
    with open("config/tags.yaml") as f:
        tags_config = yaml.safe_load(f)
    with open("config/state.yaml") as f:
        state_config = yaml.safe_load(f)
    with open("config/hardware.yaml") as f:
        hardware_config = yaml.safe_load(f)
    
    # Mock configs
    manager._configs = {
        "process": process_config,
        "tags": tags_config,
        "state": state_config,
        "hardware": hardware_config,
        "patterns": {
            "types": {
                "serpentine": {
                    "required_parameters": ["origin", "length", "spacing", "speed"],
                    "parameter_limits": {
                        "length": {"min": 10.0, "max": 500.0},
                        "spacing": {"min": 0.5, "max": 10.0},
                        "speed": {"min": 1.0, "max": 100.0}
                    }
                }
            },
            "sprayable_area": {
                "x_min": 50,
                "x_max": 450,
                "y_min": 50,
                "y_max": 450
            }
        },
        "sequences": {
            "rules": {
                "required_steps": ["move_to_trough"],
                "step_order": {
                    "move_to_trough": ["start_gas_flow"],
                    "start_gas_flow": ["start_powder_feed"]
                }
            }
        },
        "actions": {
            "move_to_trough": {
                "type": "motion",
                "parameters": {}
            },
            "start_gas_flow": {
                "type": "gas",
                "parameters": {
                    "main_flow": {"type": "float", "required": True}
                }
            }
        }
    }
    
    try:
        yield manager
    finally:
        await manager.shutdown()

@pytest.fixture
async def mock_plc_client() -> MagicMock:
    """Provide a mock PLC client."""
    client = MagicMock()
    client.get_all_tags = AsyncMock(return_value={
        "AMC.Ax1Position": 100.0,
        "AMC.Ax2Position": 200.0,
        "AOS32-0.1.2.1": 50.0
    })
    client.write_tag = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client

@pytest.fixture
async def mock_ssh_client() -> MagicMock:
    """Provide a mock SSH client."""
    client = MagicMock()
    client.write_command = AsyncMock()
    client.read_response = AsyncMock(return_value="OK")
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client

@pytest.fixture
async def state_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[StateManager, None]:
    """Provide StateManager instance."""
    manager = StateManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@pytest.fixture
async def process_validator(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[ProcessValidator, None]:
    """Provide ProcessValidator instance."""
    validator = ProcessValidator(message_broker, config_manager)
    try:
        await validator.initialize()
        yield validator
    finally:
        await validator.shutdown()

@pytest.fixture
async def action_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    process_validator: ProcessValidator
) -> AsyncGenerator[Any, None]:
    """Provide ActionManager instance."""
    from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager
    
    manager = ActionManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@pytest.fixture
async def ui_update_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager
) -> AsyncGenerator[Any, None]:
    """Provide UIUpdateManager instance."""
    from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
    
    manager = UIUpdateManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()

@pytest.fixture
async def tag_manager(
    message_broker: MessageBroker,
    config_manager: ConfigManager,
    mock_plc_client: MagicMock,
    mock_ssh_client: MagicMock
) -> AsyncGenerator[Any, None]:
    """Provide TagManager instance."""
    from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
    
    manager = TagManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    
    # Mock the clients after initialization
    manager._plc_client = mock_plc_client
    manager._ssh_client = mock_ssh_client
    
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.shutdown()
  
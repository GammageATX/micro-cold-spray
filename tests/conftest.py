"""Common test fixtures and configuration."""
import pytest
from enum import IntEnum
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import yaml

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
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
        
        # Config topics - Add these
        "config/update": set(),
        "config/update/hardware": set(), 
        "config/update/process": set(),
        "config/update/ui": set(),
        
        # Action topics
        "action/request": set(),
        "action/execute": set(),
        "action/cancel": set(),
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
        "sequence/loaded": set(),
        "sequence/status": set(),
        "sequence/step": set(),
        
        # Validation topics
        "validation/request": set(),
        "validation/response": set(),
        
        # Hardware topics
        "hardware/status/plc": set(),
        "hardware/status/motion": set(),
        "hardware/error": set(),
        
        # Data Manager topics
        "data/compressed": set(),
        "data/backup/complete": set(),
        "data/user/changed": set(),
        "data/run/status": set(),
        "data/collection/error": set(),
        "data/spray/error": set(),
        "data/saved": set(),
        "data/loaded": set(),
        "data/cleared": set(),
        "data/save/error": set(),
        "data/load/error": set(),
        "process/status/data": set(),
        "parameters/history": set()
    }
    
    try:
        await broker.start()
        yield broker
    finally:
        await broker.shutdown()

@pytest.fixture
async def config_manager(message_broker: MessageBroker) -> AsyncGenerator[MagicMock, None]:
    """Provide mocked ConfigManager."""
    mock_config = MagicMock()
    
    # Set up all required mock configs
    mock_config._configs = {
        "tags": {
            "groups": {
                "motion": {
                    "x": {
                        "position": "AMC.Ax1Position",
                        "velocity": "AMC.Ax1Velocity"
                    },
                    "y": {
                        "position": "AMC.Ax2Position",
                        "velocity": "AMC.Ax2Velocity"
                    },
                    "z": {
                        "position": "AMC.Ax3Position",
                        "velocity": "AMC.Ax3Velocity"
                    }
                },
                "gas": {
                    "main_flow": {
                        "setpoint": "AOS32-0.1.2.1",
                        "actual": "AOS32-0.1.2.2"
                    },
                    "feeder_flow": {
                        "setpoint": "AOS32-0.1.3.1",
                        "actual": "AOS32-0.1.3.2"
                    }
                }
            }
        },
        "state": {
            "transitions": {
                "INITIALIZING": {
                    "conditions": ["hardware.connected", "config.loaded"],
                    "next_states": ["READY"]
                },
                "READY": {
                    "conditions": ["hardware.connected", "hardware.enabled"],
                    "next_states": ["RUNNING", "SHUTDOWN"]
                },
                "RUNNING": {
                    "conditions": ["hardware.connected", "hardware.enabled", "sequence.active"],
                    "next_states": ["READY", "ERROR"]
                },
                "ERROR": {
                    "next_states": ["READY", "SHUTDOWN"]
                },
                "SHUTDOWN": {
                    "conditions": ["hardware.safe"],
                    "next_states": ["INITIALIZING"]
                }
            }
        },
        "hardware": {
            "motion": {
                "limits": {
                    "x": {"min": 0.0, "max": 500.0},
                    "y": {"min": 0.0, "max": 500.0},
                    "z": {"min": 0.0, "max": 200.0},
                    "velocity": {"max": 100.0},
                    "acceleration": {"max": 2000.0}
                }
            },
            "safety": {
                "gas": {
                    "main_flow": {"min": 20.0, "max": 100.0, "warning": 30.0},
                    "feeder_flow": {"min": 2.0, "max": 10.0, "warning": 3.0}
                },
                "powder": {
                    "feeder": {
                        "frequency": {"min": 100, "max": 1000},
                        "deagglomerator": {
                            "duty_cycle": {"min": 10, "max": 90}
                        }
                    }
                }
            },
            "physical": {
                "substrate_holder": {
                    "dimensions": {
                        "sprayable": {
                            "width": 500.0,
                            "height": 500.0
                        }
                    }
                },
                "hardware_sets": {
                    "set1": {
                        "nozzle": "nozzle1",
                        "feeder": "feeder1",
                        "deagglomerator": "deagg1"
                    }
                }
            }
        },
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
            }
        },
        "process": {
            "atomic_actions": {
                "motion": {
                    "move_xy": {
                        "messages": [
                            {
                                "topic": "tag/set",
                                "data": {
                                    "tag": "motion.x.position",
                                    "value": "{x}"
                                }
                            },
                            {
                                "topic": "tag/set",
                                "data": {
                                    "tag": "motion.y.position",
                                    "value": "{y}"
                                }
                            }
                        ],
                        "validation": [{
                            "tag": "motion.status",
                            "value": "complete"
                        }]
                    },
                    "home": {
                        "messages": [
                            {
                                "topic": "tag/set",
                                "data": {
                                    "tag": "motion.home",
                                    "value": True
                                }
                            }
                        ]
                    }
                },
                "gas": {
                    "set_main_flow": {
                        "messages": [
                            {
                                "topic": "tag/set",
                                "data": {
                                    "tag": "gas_control.main_flow.setpoint",
                                    "value": "{gas.main_flow}"
                                }
                            }
                        ]
                    },
                    "enable": {
                        "messages": [
                            {
                                "topic": "tag/set",
                                "data": {
                                    "tag": "gas.enable",
                                    "value": True
                                }
                            }
                        ]
                    }
                }
            },
            "action_groups": {
                "ready_system": {
                    "steps": [
                        {
                            "action": "motion.home",
                            "parameters": {}
                        },
                        {
                            "action": "gas.enable",
                            "parameters": {}
                        }
                    ]
                }
            },
            "parameters": {
                "gas": {
                    "main_flow": {
                        "min": 20.0,
                        "max": 100.0,
                        "default": 50.0
                    },
                    "feeder_flow": {
                        "min": 2.0,
                        "max": 10.0,
                        "default": 5.0
                    }
                },
                "powder": {
                    "feeder": {
                        "frequency": {
                            "min": 100,
                            "max": 1000,
                            "default": 500
                        }
                    }
                }
            }
        },
        "sequences": {
            "rules": {
                "required_steps": ["move_to_trough", "start_gas_flow"],
                "step_order": {
                    "move_to_trough": ["start_gas_flow"],
                    "start_gas_flow": ["start_powder"]
                }
            }
        }
    }
    
    # Configure mock to return configs directly (not as coroutines)
    async def get_config(name: str) -> Dict[str, Any]:
        return mock_config._configs.get(name, {})
    
    mock_config.get_config = AsyncMock(side_effect=get_config)
    mock_config.update_config = AsyncMock()
    mock_config.save_backup = AsyncMock()
    mock_config.shutdown = AsyncMock()
    
    # Add message broker
    mock_config._message_broker = message_broker
    
    try:
        yield mock_config
    finally:
        await mock_config.shutdown()

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
    # Mock state config
    state_config = {
        "transitions": {
            "INITIALIZING": {
                "conditions": ["hardware.connected", "config.loaded"],
                "next_states": ["READY"]
            },
            "READY": {
                "conditions": ["hardware.connected", "hardware.enabled"],
                "next_states": ["RUNNING", "SHUTDOWN"]
            },
            "RUNNING": {
                "conditions": ["hardware.connected", "hardware.enabled", "sequence.active"],
                "next_states": ["READY", "ERROR"]
            },
            "ERROR": {
                "next_states": ["READY", "SHUTDOWN"]
            },
            "SHUTDOWN": {
                "conditions": ["hardware.safe"],
                "next_states": ["INITIALIZING"]
            }
        }
    }
    
    # Configure mock
    config_manager.get_config.return_value = state_config
    
    manager = StateManager(message_broker, config_manager)
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
  
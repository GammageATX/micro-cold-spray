# pytest -v --asyncio-mode=auto

"""Common test fixtures and configuration."""
import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import yaml
from pathlib import Path

# Core infrastructure
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager

# Process components
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.components.process.data.data_manager import DataManager

# Operation components
from micro_cold_spray.core.components.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.components.operations.patterns.pattern_manager import PatternManager

# UI components
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager

# Core exceptions
from micro_cold_spray.core.exceptions import CoreError


class TestOrder:
    """Test execution order constants."""
    INFRASTRUCTURE = 1
    PROCESS = 2
    OPERATIONS = 3
    UI = 4


def order(value: int):
    """Decorator to set test order."""
    def _order(f):
        f.test_order = value
        return f
    return _order


def load_config(config_name: str) -> Dict[str, Any]:
    """Load config file without writing."""
    try:
        config_path = Path("config") / f"{config_name}.yaml"
        if not config_path.exists():
            context = {
                "config_name": config_name,
                "path": str(config_path),
                "available": [p.stem for p in Path("config").glob("*.yaml")]
            }
            raise CoreError("Config file not found", context)

        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        context = {
            "config_name": config_name,
            "error": str(e),
            "path": str(config_path)
        }
        raise CoreError("Failed to load config", context) from e


@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Create message broker instance."""
    broker = MessageBroker(test_mode=True)
    await broker.start()
    yield broker
    await broker.shutdown()


@pytest.fixture
async def config_manager(message_broker) -> AsyncGenerator[ConfigManager, None]:
    """Create config manager instance with real configs."""
    mock_config = MagicMock(spec=ConfigManager)

    # Load all real configs
    try:
        mock_config._configs = {
            'application': load_config('application'),
            'hardware': load_config('hardware'),
            'operation': load_config('operation'),
            'process': load_config('process'),
            'state': load_config('state'),
            'tags': load_config('tags')
        }
    except CoreError as e:
        pytest.skip(f"Config loading failed: {e.context}")

    # Configure mock to return configs directly
    async def get_config(name: str) -> Dict[str, Any]:
        if name not in mock_config._configs:
            context = {
                "requested": name,
                "available": list(mock_config._configs.keys())
            }
            raise CoreError("Config not found", context)
        return mock_config._configs[name]

    mock_config.get_config = AsyncMock(side_effect=get_config)
    mock_config.update_config = AsyncMock()
    mock_config.save_backup = AsyncMock()
    mock_config._message_broker = message_broker

    # Initialize and cleanup are now async
    mock_config.initialize = AsyncMock()
    mock_config.shutdown = AsyncMock()

    await mock_config.initialize()
    yield mock_config
    await mock_config.shutdown()


@pytest.fixture
async def process_validator(
    message_broker,
    config_manager
) -> AsyncGenerator[ProcessValidator, None]:
    """Create process validator instance."""
    validator = ProcessValidator(
        message_broker=message_broker,
        config_manager=config_manager
    )
    await validator.initialize()
    yield validator
    await validator.shutdown()


@pytest.fixture
async def action_manager(
    message_broker,
    config_manager,
    process_validator
) -> AsyncGenerator[ActionManager, None]:
    """Create action manager instance."""
    manager = ActionManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def pattern_manager(
    message_broker,
    config_manager,
    process_validator
) -> AsyncGenerator[PatternManager, None]:
    """Create pattern manager instance."""
    manager = PatternManager(
        message_broker=message_broker,
        config_manager=config_manager,
        process_validator=process_validator
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def ui_manager(
    message_broker,
    config_manager,
    data_manager
) -> AsyncGenerator[UIUpdateManager, None]:
    """Create UI update manager instance."""
    manager = UIUpdateManager(
        message_broker=message_broker,
        config_manager=config_manager,
        data_manager=data_manager
    )
    await manager.initialize()
    yield manager

    # Cleanup all registered widgets before manager
    for widget_id in list(manager._registered_widgets.keys()):
        await manager.unregister_widget(widget_id)
    await manager.shutdown()


@pytest.fixture
async def data_manager(
    message_broker,
    config_manager
) -> AsyncGenerator[DataManager, None]:
    """Create data manager instance."""
    manager = DataManager(
        message_broker=message_broker,
        config_manager=config_manager
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()

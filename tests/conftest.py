# pytest -v --asyncio-mode=auto

"""Common test fixtures and configuration."""
import pytest
from typing import AsyncGenerator, Dict, Any
import yaml
from pathlib import Path
import logging
from pytest_mock import MockerFixture

# Core infrastructure
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager

# Process components
from micro_cold_spray.core.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.process.data.data_manager import DataManager
from micro_cold_spray.core.process.operations.actions.action_manager import ActionManager
from micro_cold_spray.core.process.operations.patterns.pattern_manager import PatternManager
from micro_cold_spray.core.process.operations.parameters.parameter_manager import ParameterManager
from micro_cold_spray.core.process.operations.sequences.sequence_manager import SequenceManager

# UI components
from micro_cold_spray.core.ui.managers.ui_update_manager import UIUpdateManager

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


# Infrastructure Fixtures
@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Create message broker instance."""
    broker = MessageBroker()
    await broker.start()
    yield broker
    await broker.shutdown()


@pytest.fixture
async def config_manager(message_broker) -> AsyncGenerator[ConfigManager, None]:
    """Create config manager instance with real config files."""
    config_path = Path("config").resolve()
    if not config_path.exists():
        raise RuntimeError(f"Config directory not found: {config_path}")

    config_manager = ConfigManager(config_path, message_broker)
    await config_manager.initialize()
    yield config_manager
    await config_manager.shutdown()


@pytest.fixture
async def state_manager(config_manager) -> AsyncGenerator[StateManager, None]:
    """Create state manager instance."""
    state_manager = StateManager(config_manager)
    await state_manager.initialize()
    yield state_manager
    await state_manager.shutdown()


@pytest.fixture
async def tag_manager(config_manager, mocker: MockerFixture) -> AsyncGenerator[TagManager, None]:
    """Create tag manager instance."""
    # Create mock PLC client
    plc_client = mocker.AsyncMock()
    plc_client.read_tag.return_value = 0
    plc_client.write_tag.return_value = None

    # Create mock SSH client
    ssh_client = mocker.AsyncMock()
    ssh_client.read_command.return_value = 0
    ssh_client.write_command.return_value = None

    # Create tag manager with mocked clients
    tag_manager = TagManager(config_manager)
    tag_manager._plc_client = plc_client
    tag_manager._ssh_client = ssh_client
    await tag_manager.initialize()
    yield tag_manager
    await tag_manager.shutdown()


# Process Fixtures
@pytest.fixture
async def process_validator(message_broker, config_manager) -> AsyncGenerator[ProcessValidator, None]:
    """Create process validator instance."""
    validator = ProcessValidator(message_broker, config_manager)
    await validator.initialize()
    yield validator
    await validator.shutdown()


@pytest.fixture
async def data_manager(message_broker, config_manager) -> AsyncGenerator[DataManager, None]:
    """Create data manager instance."""
    manager = DataManager(message_broker, config_manager)
    await manager.initialize()
    yield manager
    await manager.shutdown()


# Operation Fixtures
@pytest.fixture
async def action_manager(message_broker, config_manager, process_validator) -> AsyncGenerator[ActionManager, None]:
    """Create action manager instance."""
    manager = ActionManager(message_broker, config_manager, process_validator)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def pattern_manager(message_broker, config_manager) -> AsyncGenerator[PatternManager, None]:
    """Create pattern manager instance."""
    manager = PatternManager(message_broker, config_manager)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def parameter_manager(message_broker, config_manager, process_validator) -> AsyncGenerator[ParameterManager, None]:
    """Create parameter manager instance."""
    manager = ParameterManager(message_broker, config_manager, process_validator)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def sequence_manager(message_broker, config_manager, action_manager) -> AsyncGenerator[SequenceManager, None]:
    """Create sequence manager instance."""
    manager = SequenceManager(message_broker, config_manager, action_manager)
    await manager.initialize()
    yield manager
    await manager.shutdown()


# UI Fixtures
@pytest.fixture
async def ui_manager(message_broker, config_manager, data_manager) -> AsyncGenerator[UIUpdateManager, None]:
    """Create UI update manager instance."""
    manager = UIUpdateManager(message_broker, config_manager, data_manager)
    await manager.initialize()
    yield manager

    # Cleanup all registered widgets before manager
    for widget_id in list(manager._registered_widgets.keys()):
        await manager.unregister_widget(widget_id)
    await manager.shutdown()


# Qt Application Fixture (for UI tests)
@pytest.fixture
def qapp():
    """Create Qt application instance."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

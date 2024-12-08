"""Data Manager test suite.

Tests data management functionality:
- File listing and saving
- Request/response patterns
- State updates
- Error handling

Run with:
    pytest tests/process/test_data_manager.py -v --asyncio-mode=auto
"""

import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from pathlib import Path
from tests.conftest import TestOrder, order
import shutil
from datetime import datetime

from micro_cold_spray.core.process.data.data_manager import DataManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager


@pytest.fixture
async def message_broker() -> AsyncGenerator[MessageBroker, None]:
    """Provide a MessageBroker instance."""
    broker = MessageBroker()
    broker._test_mode = True  # Enable test mode to bypass topic validation
    await broker.start()

    # Set valid topics for testing
    valid_topics = {
        "test/request", "test/response",
        "error",
        "config/request", "config/response", "config/update",
        "data/request", "data/response", "data/state",
        "tag/request", "tag/response", "tag/update",
        "hardware/state",
        "sequence/request", "sequence/response", "sequence/error",
        "sequence/status", "sequence/state", "sequence/step",
        "sequence/loaded", "sequence/complete"
    }
    await broker.set_valid_topics(valid_topics)
    broker._initialized = True

    yield broker
    await broker.shutdown()


@pytest.fixture
async def config_manager(message_broker: MessageBroker, tmp_path: Path) -> AsyncGenerator[ConfigManager, None]:
    """Provide a ConfigManager instance."""
    # Create test config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Copy real configs to temp directory
    real_configs = Path("config")
    for config_file in real_configs.glob("*.yaml"):
        shutil.copy(config_file, config_dir)

    manager = ConfigManager(config_dir, message_broker)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def data_manager(message_broker: MessageBroker, config_manager: ConfigManager, tmp_path: Path) -> AsyncGenerator[DataManager, None]:
    """Provide a DataManager instance."""
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    manager = DataManager(message_broker, config_manager, data_root=data_root)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@order(TestOrder.PROCESS)
class TestDataManager:
    """Data management tests run after process components."""

    @pytest.mark.asyncio
    async def test_file_listing(self, data_manager: DataManager, tmp_path: Path) -> None:
        """Test file listing functionality."""
        # Create test files
        param_dir = tmp_path / "data/parameters"
        param_dir.mkdir(parents=True, exist_ok=True)
        (param_dir / "test1.yaml").write_text("test: 1")
        (param_dir / "test2.yaml").write_text("test: 2")

        # Track responses and state updates
        responses: list[Dict[str, Any]] = []
        states: list[Dict[str, Any]] = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        await data_manager._message_broker.subscribe("data/response", collect_responses)
        await data_manager._message_broker.subscribe("data/state", collect_states)

        # Request file listing
        request_id = "test-list-123"
        await data_manager._message_broker.publish(
            "data/request",
            {
                "request_id": request_id,
                "request_type": "list",
                "type": "parameters"
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        assert responses[0]["request_id"] == request_id
        assert responses[0]["success"] is True
        assert "files" in responses[0]["data"]

        # Verify state update
        assert len(states) == 1
        assert states[0]["operation"] == "list"
        assert states[0]["type"] == "parameters"
        assert states[0]["state"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_file_loading(self, data_manager: DataManager, tmp_path: Path) -> None:
        """Test file loading functionality."""
        # Create test nozzle file first
        nozzle_data = {
            "nozzle": {
                "name": "Test Nozzle",
                "manufacturer": "Test",
                "type": "Cold Spray",
                "description": "Test nozzle file"
            }
        }
        nozzle_dir = tmp_path / "data/parameters/nozzles"
        nozzle_dir.mkdir(parents=True, exist_ok=True)
        nozzle_file = nozzle_dir / "test_nozzle.yaml"
        import yaml
        with open(nozzle_file, "w") as f:
            yaml.dump(nozzle_data, f)

        # Create test parameter file
        test_data = {
            "metadata": {
                "name": "test",
                "version": "1.0",
                "created": datetime.now().strftime("%Y-%m-%d"),
                "author": "test_user",
                "description": "Test parameter file"
            },
            "nozzle": {
                "type": "Test Nozzle"
            },
            "gas_flows": {
                "gas_type": "N2",
                "main_gas": 50.0,
                "feeder_gas": 5.0
            },
            "powder_feed": {
                "frequency": 600,
                "deagglomerator": {
                    "speed": "Medium"
                }
            }
        }
        param_dir = tmp_path / "data/parameters"
        param_dir.mkdir(parents=True, exist_ok=True)
        test_file = param_dir / "test.yaml"
        with open(test_file, "w") as f:
            yaml.dump(test_data, f)

        # Track responses and state updates
        responses: list[Dict[str, Any]] = []
        states: list[Dict[str, Any]] = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        await data_manager._message_broker.subscribe("data/response", collect_responses)
        await data_manager._message_broker.subscribe("data/state", collect_states)

        # Request file load
        request_id = "test-load-123"
        await data_manager._message_broker.publish(
            "data/request",
            {
                "request_id": request_id,
                "request_type": "load",
                "type": "parameters",
                "name": "test"
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        print(f"Response data: {responses[0]}")
        print(f"Test data: {test_data}")
        assert responses[0]["request_id"] == request_id
        assert responses[0]["success"] is True
        assert responses[0]["data"] == test_data

        # Verify state update
        assert len(states) == 1
        assert states[0]["operation"] == "load"
        assert states[0]["type"] == "parameters"
        assert states[0]["name"] == "test"
        assert states[0]["state"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_file_saving(self, data_manager: DataManager, tmp_path: Path) -> None:
        """Test file saving functionality."""
        # Create test nozzle file first
        nozzle_data = {
            "nozzle": {
                "name": "Test Nozzle",
                "manufacturer": "Test",
                "type": "Cold Spray",
                "description": "Test nozzle file"
            }
        }
        nozzle_dir = tmp_path / "data/parameters/nozzles"
        nozzle_dir.mkdir(parents=True, exist_ok=True)
        nozzle_file = nozzle_dir / "test_nozzle.yaml"
        import yaml
        with open(nozzle_file, "w") as f:
            yaml.dump(nozzle_data, f)

        test_data = {
            "metadata": {
                "name": "test",
                "version": "1.0",
                "created": datetime.now().strftime("%Y-%m-%d"),
                "author": "test_user",
                "description": "Test parameter file"
            },
            "nozzle": {
                "type": "Test Nozzle"
            },
            "gas_flows": {
                "gas_type": "N2",
                "main_gas": 50.0,
                "feeder_gas": 5.0
            },
            "powder_feed": {
                "frequency": 600,
                "deagglomerator": {
                    "speed": "Medium"
                }
            }
        }

        # Track responses and state updates
        responses: list[Dict[str, Any]] = []
        states: list[Dict[str, Any]] = []

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        async def collect_states(data: Dict[str, Any]) -> None:
            states.append(data)

        await data_manager._message_broker.subscribe("data/response", collect_responses)
        await data_manager._message_broker.subscribe("data/state", collect_states)

        # Request file save
        request_id = "test-save-123"
        await data_manager._message_broker.publish(
            "data/request",
            {
                "request_id": request_id,
                "request_type": "save",
                "type": "parameters",
                "name": "test",
                "data": test_data
            }
        )
        await asyncio.sleep(0.1)

        # Verify response
        assert len(responses) == 1
        assert responses[0]["request_id"] == request_id
        assert responses[0]["success"] is True

        # Verify state update
        assert len(states) == 1
        assert states[0]["operation"] == "save"
        assert states[0]["type"] == "parameters"
        assert states[0]["name"] == "test"
        assert states[0]["state"] == "COMPLETED"

        # Verify file was saved
        param_dir = tmp_path / "data/parameters"
        test_file = param_dir / "test.yaml"
        assert test_file.exists()

    @pytest.mark.asyncio
    async def test_error_handling(self, data_manager: DataManager) -> None:
        """Test error handling."""
        # Track error messages and responses
        errors: list[Dict[str, Any]] = []
        responses: list[Dict[str, Any]] = []

        async def collect_errors(data: Dict[str, Any]) -> None:
            errors.append(data)

        async def collect_responses(data: Dict[str, Any]) -> None:
            responses.append(data)

        await data_manager._message_broker.subscribe("error", collect_errors)
        await data_manager._message_broker.subscribe("data/response", collect_responses)

        # Test invalid request type
        request_id = "test-error-123"
        await data_manager._message_broker.publish(
            "data/request",
            {
                "request_id": request_id,
                "request_type": "invalid",
                "type": "parameters"
            }
        )
        await asyncio.sleep(0.1)

        # Verify error response
        assert len(responses) == 1
        assert responses[0]["request_id"] == request_id
        assert responses[0]["success"] is False
        assert "Invalid request_type" in responses[0]["error"]

        # Verify error published with context
        assert len(errors) == 1
        assert errors[0]["source"] == "data_manager"
        assert "Invalid request_type" in errors[0]["error"]
        assert errors[0]["request_id"] == request_id
        assert errors[0]["context"]["request_type"] == "invalid"
        assert errors[0]["context"]["type"] == "parameters"

        # Test missing file type
        request_id = "test-error-456"
        await data_manager._message_broker.publish(
            "data/request",
            {
                "request_id": request_id,
                "request_type": "list",
                "type": ""
            }
        )
        await asyncio.sleep(0.1)

        # Verify error response
        assert len(responses) == 2
        assert responses[1]["request_id"] == request_id
        assert responses[1]["success"] is False
        assert "No file type specified" in responses[1]["error"]

        # Verify error published with context
        assert len(errors) == 2
        assert errors[1]["source"] == "data_manager"
        assert "No file type specified" in errors[1]["error"]
        assert errors[1]["request_id"] == request_id
        assert errors[1]["context"]["request_type"] == "list"
        assert errors[1]["context"]["type"] == ""

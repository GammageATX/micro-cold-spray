"""Integration test fixtures."""

import pytest
from fastapi.testclient import TestClient

from micro_cold_spray.__main__ import app
from micro_cold_spray.core.config.app import app as config_app
from micro_cold_spray.core.communication.app import app as communication_app
from micro_cold_spray.core.process.app import app as process_app
from micro_cold_spray.core.state.app import app as state_app
from micro_cold_spray.core.data_collection.app import app as data_collection_app
from micro_cold_spray.core.validation.app import app as validation_app
from micro_cold_spray.core.messaging.app import app as messaging_app
from micro_cold_spray.ui.app import app as ui_app


@pytest.fixture
def main_client():
    """Create test client for main application."""
    return TestClient(app)


@pytest.fixture
def ui_client():
    """Create test client for UI service."""
    return TestClient(ui_app)


@pytest.fixture
def config_client():
    """Create test client for Config service."""
    return TestClient(config_app)


@pytest.fixture
def communication_client():
    """Create test client for Communication service."""
    return TestClient(communication_app)


@pytest.fixture
def process_client():
    """Create test client for Process service."""
    return TestClient(process_app)


@pytest.fixture
def state_client():
    """Create test client for State service."""
    return TestClient(state_app)


@pytest.fixture
def data_collection_client():
    """Create test client for Data Collection service."""
    return TestClient(data_collection_app)


@pytest.fixture
def validation_client():
    """Create test client for Validation service."""
    return TestClient(validation_app)


@pytest.fixture
def messaging_client():
    """Create test client for Messaging service."""
    return TestClient(messaging_app)

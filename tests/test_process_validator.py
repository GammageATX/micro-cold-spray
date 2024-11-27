# tests/test_process_validator.py
import yaml
import pytest
from unittest.mock import MagicMock
from micro_cold_spray.core.components.process.validation.process_validator import ProcessValidator
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager

@pytest.fixture
def message_broker():
    broker = MessageBroker()
    broker._subscribers = {}  # Reset subscribers for clean test environment
    return broker

@pytest.fixture
def config_manager(message_broker):
    # Load the actual configuration files
    with open('config/process.yaml', 'r') as f:
        process_config = yaml.safe_load(f)
    
    config_manager = ConfigManager(message_broker)
    config_manager._configs = {
        'process': process_config
    }
    return config_manager

@pytest.fixture
def process_validator(message_broker, config_manager):
    return ProcessValidator(message_broker, config_manager)

def test_process_validator_initialization(process_validator):
    assert process_validator is not None
    assert isinstance(process_validator, ProcessValidator)

def test_process_validator_validate_parameters(process_validator):
    parameters = {
        "motion": {
            "axis": "x",
            "distance": 10,
            "velocity": 5,
            "acceleration": 2,
            "deceleration": 2
        },
        "process": {
            "temperature": 300,
            "pressure": 50
        }
    }
    result = process_validator.validate_parameters(parameters)
    assert result["valid"]
    assert len(result["errors"]) == 0

def test_process_validator_invalid_parameters(process_validator):
    parameters = {
        "motion": {
            "axis": "x",
            "distance": -1000,  # Invalid distance
            "velocity": 5000,   # Invalid velocity
            "acceleration": -10,  # Invalid acceleration
            "deceleration": -10   # Invalid deceleration
        },
        "process": {
            "temperature": -100,  # Invalid temperature
            "pressure": 10000     # Invalid pressure
        }
    }
    result = process_validator.validate_parameters(parameters)
    assert not result["valid"]
    assert len(result["errors"]) > 0